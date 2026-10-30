"""Eventos reales de PLM en dos conexiones; datos solo en la copia neutralizada."""

# stdout es el protocolo que el wrapper valida por fases; no es logging de producto.
# pylint: disable=unknown-option-value,print-used

import concurrent.futures
import json
from datetime import date, datetime
from threading import Barrier

from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import SUPERUSER_ID, Command, api, fields
from odoo.exceptions import AccessError


def _fixture(registry, context):  # pylint: disable=too-many-locals
    with registry.cursor() as cursor:
        test_env = api.Environment(cursor, SUPERUSER_ID, context)
        assert not test_env["ir.cron"].search_count([("active", "=", True)])
        assert not test_env["ir.mail_server"].search_count([("active", "=", True)])
        assert test_env["ir.config_parameter"].get_param("mc_rov.entorno") == "STAGING"
        assert (
            test_env["ir.config_parameter"].get_param("web.base.url")
            == "http://127.0.0.1/isolated-concurrency"
        )
        company = test_env.company
        category = test_env["product.category"].create({"name": "QA Ingeniería concurrente"})
        test_env["ir.config_parameter"].set_param("mc_rov.rov_category_id", str(category.id))
        product = test_env["product.template"].create(
            {"name": "QA Ingeniería concurrente", "categ_id": category.id}
        )
        users = []
        for index, timezone in enumerate(("UTC", "Asia/Tokyo")):
            users.append(
                test_env["res.users"].create(
                    {
                        "name": "QA Ingeniería concurrente " + str(index + 1),
                        "login": "qa_engineering_concurrent_" + str(index + 1),
                        "company_id": company.id,
                        "company_ids": [Command.set(company.ids)],
                        "tz": timezone,
                        "group_ids": [
                            Command.set(
                                [
                                    test_env.ref("base.group_user").id,
                                    test_env.ref("mrp_plm.group_plm_user").id,
                                ]
                            )
                        ],
                    }
                )
            )
        eco_type = test_env["mrp.eco.type"].create({"name": "QA Ingeniería circuito concurrente"})
        stage = test_env["mrp.eco.stage"].create(
            {
                "name": "QA Aplicable solo tras dos aprobaciones",
                "sequence": 10,
                "type_ids": [Command.set(eco_type.ids)],
                "allow_apply_change": True,
            }
        )
        # Plantillas distintas: dos aprobadores escriben filas distintas. Un solo
        # template compartido no comprobaría el riesgo de write skew entre aprobaciones.
        for index, user in enumerate(users):
            test_env["mrp.eco.approval.template"].create(
                {
                    "name": "QA Aprobación obligatoria " + str(index + 1),
                    "stage_id": stage.id,
                    "approval_type": "mandatory",
                    "user_ids": [Command.set(user.ids)],
                }
            )
        policies = test_env["mc.rov.engineering.activity.policy"]
        policy = policies.search([("company_id", "=", company.id)], limit=1)
        values = {
            "enabled": True,
            "prepare_user_id": users[0].id,
            "apply_user_id": users[0].id,
            "prepare_employee_id": False,
            "apply_employee_id": False,
            "lead_years": 1,
            "tz": "America/Santiago",
        }
        if policy:
            policy.write(values)
        else:
            policy = policies.create({"company_id": company.id, **values})
        controls = test_env["mc.rov.automation.control"]
        control = controls.search([("company_id", "=", company.id)], limit=1)
        if control:
            control.enabled = True
        else:
            controls.create({"company_id": company.id, "enabled": True})
        assert policy._deadline(datetime(2024, 2, 29, 15)) == date(2025, 2, 28)
        assert policy._deadline(datetime(2026, 1, 1, 1)) == date(2026, 12, 31)
        fixture = {
            "company": company.id,
            "product": product.id,
            "type": eco_type.id,
            "stage": stage.id,
            "users": [user.id for user in users],
        }
        cursor.commit()
        return fixture


def _race(registry, context, fixture, phase, eco_id=None):
    barrier = Barrier(2, timeout=15)

    def worker(index):
        first_pid, first_read = None, None
        for attempt in range(1, 4):
            try:
                with registry.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout = '15s'")
                    cursor.execute("SET LOCAL statement_timeout = '30s'")
                    worker_env = api.Environment(cursor, fixture["users"][index], context)
                    service = worker_env["mc.rov.engineering.activity.automation"]
                    eco = worker_env["mrp.eco"].browse(eco_id) if eco_id else None
                    if attempt == 1:
                        first_read = (
                            {
                                "state": eco.state,
                                "active": eco.active,
                                "applicable": service._applicable(eco),
                            }
                            if eco
                            else {
                                "product_version": worker_env["product.template"]
                                .browse(fixture["product"])
                                .version
                            }
                        )
                        cursor.execute("SELECT pg_backend_pid()")
                        first_pid = cursor.fetchone()[0]
                        barrier.wait()
                    if phase == "create":
                        eco = worker_env["mrp.eco"].create(
                            {
                                "name": "QA Ingeniería carrera " + str(index + 1),
                                "type": "product",
                                "product_tmpl_id": fixture["product"],
                                "type_id": fixture["type"],
                                "stage_id": fixture["stage"],
                                "company_id": fixture["company"],
                            }
                        )
                    elif phase == "duplicate_delivery":
                        service._start(eco, "prepare", fields.Datetime.now())
                    elif phase == "approvals":
                        eco.approve()
                    elif phase == "apply":
                        eco.action_apply()
                    elif phase == "archive":
                        eco.action_archive()
                    elif phase == "unarchive":
                        eco.action_unarchive()
                    else:
                        raise AssertionError("Unknown engineering race phase")
                    cursor.commit()
                    return {
                        "attempts": attempt,
                        "pid": first_pid,
                        "read": first_read,
                        "result": "committed",
                        "eco": eco.id,
                    }
            except (SerializationFailure, DeadlockDetected):
                # Cursor y cachés nuevos: repetir la transacción completa, como una RPC.
                if attempt == 3:
                    raise
        raise AssertionError("Unreachable")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, index) for index in range(2)]
        results = [future.result(timeout=60) for future in futures]
    assert all(isinstance(row["pid"], int) and row["pid"] > 0 for row in results), results
    assert len({row["pid"] for row in results}) == 2, results
    if phase != "create":
        assert results[0]["read"] == results[1]["read"], results
    return results


def _check(
    registry, context, fixture, ids, expected, phase, workers, native_before=None
):  # pylint: disable=too-many-arguments,too-many-locals
    with registry.cursor() as cursor:
        check_env = api.Environment(cursor, SUPERUSER_ID, context)
        ecos = check_env["mrp.eco"].with_context(active_test=False).browse(ids)
        cycles = check_env["mc.rov.engineering.activity.cycle"].search([("eco_id", "in", ids)])
        runs = check_env["mc.rov.engineering.activity.run"].search(
            [("eco_id", "in", ids)], order="id"
        )
        types = check_env.ref("mc_rov.activity_type_engineering_prepare") | check_env.ref(
            "mc_rov.activity_type_engineering_apply"
        )
        activities = (
            check_env["mail.activity"]
            .with_context(active_test=False)
            .search(
                [
                    ("res_model", "=", "mrp.eco"),
                    ("res_id", "in", ids),
                    ("activity_type_id", "in", types.ids),
                ]
            )
        )
        active = activities.filtered("active")
        assert len(cycles) == len(ids) and set(cycles.eco_id.ids) == set(ids)
        assert len(runs) == expected["runs"], (phase, runs.ids)
        assert len(active) == expected["pending"], (phase, active.ids)
        assert len(runs.filtered(lambda run: run.outcome == "pending")) == len(active)
        assert set(activities.ids) == set(runs.activity_id.ids), (
            "Orphan engineering activity: " + phase
        )
        assert len({(run.cycle_id.id, run.event, run.stage) for run in runs}) == len(runs)
        assert all(
            eco.state == expected["state"] and eco.active == expected["active"] for eco in ecos
        )
        policy = check_env["mc.rov.engineering.activity.policy"].search(
            [("company_id", "=", fixture["company"])]
        )
        for cycle in cycles:
            assert cycle.original_deadline == policy._deadline(cycle.eco_id.create_date)
            assert cycle.current_deadline == cycle.original_deadline
            assert cycle.deadline_tz == "America/Santiago" and cycle.lead_years == 1
            assert cycle.event_sequence == expected["sequence"], (phase, cycle.event_sequence)
        for run in runs:
            assert run.original_deadline == run.cycle_id.original_deadline
            assert run.current_deadline == run.original_deadline
            if run.outcome != "pending":
                assert (
                    run.finished_at
                    and run.finished_by_id.id in fixture["users"]
                    and run.finish_reason
                )
        if active:
            assert all(activity.user_id.id == fixture["users"][0] for activity in active)
            assert all(
                activity.date_deadline
                == policy._deadline(check_env["mrp.eco"].browse(activity.res_id).create_date)
                for activity in active
            )
        if native_before is not None:
            native = (
                check_env["mail.activity"]
                .with_context(active_test=False)
                .browse([row["id"] for row in native_before])
            )
            assert (
                native.exists().read(["user_id", "date_deadline", "activity_type_id", "active"])
                == native_before
            ), "Native approval activities changed"
        if phase == "approvals":
            approvals = ecos.approval_ids.filtered(lambda row: not row.is_closed)
            assert len(approvals) == 2 and set(approvals.mapped("status")) == {"approved"}
            assert set(approvals.user_id.ids) == set(fixture["users"])
            assert set(runs.mapped("stage")) == {"prepare", "apply"}
        print(
            "ENGINEERING_CONCURRENCY_CASE="
            + json.dumps(
                {
                    "phase": phase,
                    "workers": workers,
                    "cycles": len(cycles),
                    "runs": len(runs),
                    "activities": len(activities),
                    "active_pending": len(active),
                    "orphan_activities": 0,
                    "anniversary_preserved": True,
                    "native_approvals_verified": native_before is not None,
                }
            )
        )


def _enable_product_write(registry, context, fixture, eco_id):
    """Aplicar una revisión requiere el permiso nativo de escribir su producto."""
    with registry.cursor() as cursor:
        setup = api.Environment(cursor, SUPERUSER_ID, context)
        eco = setup["mrp.eco"].browse(eco_id)
        product = eco.product_tmpl_id
        before_version = product.version
        runs = setup["mc.rov.engineering.activity.run"].search([("eco_id", "=", eco_id)])
        before = runs.read(["outcome", "activity_id", "original_deadline", "current_deadline"])
        denied_users = set()
        for user_id in fixture["users"]:
            assert eco.with_user(user_id).has_access("write")
            assert not product.with_user(user_id).has_access("write")
            try:
                with cursor.savepoint():
                    eco.with_user(user_id).action_apply()
            except AccessError:
                denied_users.add(user_id)
            else:
                raise AssertionError("Native apply must reject an actor without product write")
        assert denied_users == set(fixture["users"])
        assert eco.state == "progress" and product.version == before_version
        assert (
            runs.read(["outcome", "activity_id", "original_deadline", "current_deadline"])
            == before
        )
        # Solo los usuarios ficticios de esta copia reciben el grupo nativo. No sudo
        # en los eventos: las carreras siguen usando dos actores y conexiones propios.
        group = setup.ref("product.group_product_manager")
        setup["res.users"].browse(fixture["users"]).write({"group_ids": [Command.link(group.id)]})
        assert all(product.with_user(user_id).has_access("write") for user_id in fixture["users"])
        cursor.commit()
    print("ENGINEERING_CONCURRENCY_NATIVE_PRODUCT_PERMISSION=VERIFIED")


def run_probe(registry, database):
    if not database.startswith("mc_rov_engineering_ci_"):
        raise AssertionError("Engineering concurrency requires its isolated CI database")
    context = {
        "tracking_disable": True,
        "mail_create_nosubscribe": True,
        "no_reset_password": True,
        "mail_notify_force_send": False,
    }
    fixture = _fixture(registry, context)
    context["allowed_company_ids"] = [fixture["company"]]
    results = _race(registry, context, fixture, "create")
    ids = [row["eco"] for row in results]
    assert len(set(ids)) == 2
    expected = {"runs": 2, "pending": 2, "state": "confirmed", "active": True, "sequence": 1}
    _check(registry, context, fixture, ids, expected, "create", results)
    main, remaining = ids
    expected.update(runs=1, pending=1)
    results = _race(registry, context, fixture, "duplicate_delivery", main)
    _check(registry, context, fixture, [main], expected, "duplicate_delivery", results)
    with registry.cursor() as cursor:
        setup = api.Environment(cursor, fixture["users"][0], context)
        eco = setup["mrp.eco"].browse(main)
        eco.action_new_revision()
        native = eco.activity_ids.filtered(
            lambda row: row.activity_type_id == setup.ref("mail.mail_activity_data_todo")
        )
        assert len(native) == 2
        native_before = native.read(["user_id", "date_deadline", "activity_type_id", "active"])
        assert not setup["mc.rov.engineering.activity.automation"]._applicable(eco)
        cursor.commit()
    results = _race(registry, context, fixture, "approvals", main)
    expected.update(runs=2, pending=1, state="progress", sequence=2)
    _check(registry, context, fixture, [main], expected, "approvals", results, native_before)
    _enable_product_write(registry, context, fixture, main)
    results = _race(registry, context, fixture, "apply", main)
    expected.update(pending=0, state="done", sequence=3)
    _check(registry, context, fixture, [main], expected, "apply", results, native_before)
    results = _race(registry, context, fixture, "archive", remaining)
    expected.update(runs=1, pending=0, state="confirmed", active=False, sequence=2)
    _check(registry, context, fixture, [remaining], expected, "archive", results)
    results = _race(registry, context, fixture, "unarchive", remaining)
    expected.update(runs=2, pending=1, active=True, sequence=3)
    _check(registry, context, fixture, [remaining], expected, "unarchive", results)
    print("ENGINEERING_CONCURRENCY_ANNIVERSARY=PASSED")
    print("ENGINEERING_CONCURRENCY_PROBE=PASSED")


# El shell aporta el registro; su transacción inicial nunca se confirma.
shell_env = globals()["env"]
shell_env.cr.rollback()
run_probe(shell_env.registry, shell_env.cr.dbname)
