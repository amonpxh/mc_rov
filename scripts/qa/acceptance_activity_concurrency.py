"""Ejercita eventos nativos solo en una copia neutralizada de STAGING."""

import concurrent.futures
import json
from threading import Barrier

from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import SUPERUSER_ID, Command, api
from odoo.exceptions import UserError


def _fixture(registry, context):  # pylint: disable=too-many-locals
    with registry.cursor() as cursor:
        setup = api.Environment(cursor, SUPERUSER_ID, context)
        assert not setup["ir.cron"].search_count([("active", "=", True)])
        assert not setup["ir.mail_server"].search_count([("active", "=", True)])
        company = setup.company
        category = setup["product.category"].create({"name": "QA aceptación concurrente"})
        setup["ir.config_parameter"].set_param("mc_rov.rov_category_id", str(category.id))
        product = setup["product.product"].create(
            {"name": "QA aceptación concurrente", "tracking": "serial", "categ_id": category.id}
        )
        lot = setup["stock.lot"].create(
            {
                "name": "QA-ACCEPTANCE-CONCURRENT",
                "product_id": product.id,
                "company_id": company.id,
            }
        )
        user = setup["res.users"].create(
            {
                "name": "QA Taller aceptación concurrente",
                "login": "qa_acceptance_concurrent",
                "company_id": company.id,
                "company_ids": [Command.set(company.ids)],
                "group_ids": [
                    Command.set(
                        [
                            setup.ref(xmlid).id
                            for xmlid in (
                                "base.group_user",
                                "mrp.group_mrp_user",
                                "stock.group_stock_user",
                            )
                        ]
                    )
                ],
            }
        )
        employee = setup["hr.employee"].create(
            {"name": "QA técnico aceptación concurrente", "company_id": company.id}
        )
        calendar = setup["resource.calendar"].create(
            {
                "name": "QA aceptación lunes a viernes",
                "tz": "America/Santiago",
                "company_id": company.id,
                "attendance_ids": [Command.clear()]
                + [
                    Command.create(
                        {
                            "name": "QA jornada",
                            "dayofweek": str(day),
                            "hour_from": 8,
                            "hour_to": 17,
                            "day_period": "morning",
                        }
                    )
                    for day in range(5)
                ],
            }
        )
        # Aislar aceptación de políticas ajenas copiadas desde STAGING.
        for model in (
            "mc.rov.repair.activity.policy",
            "mc.rov.manufacturing.activity.policy",
            "mc.rov.quality.activity.policy",
        ):
            setup[model].search([("company_id", "=", company.id)]).write({"enabled": False})
        control = setup["mc.rov.automation.control"].search([("company_id", "=", company.id)])
        if control:
            control.enabled = True
        policies = setup["mc.rov.acceptance.activity.policy"]
        policy = policies.search([("company_id", "=", company.id)], limit=1)
        values = {
            "enabled": True,
            "user_id": user.id,
            "employee_id": False,
            "calendar_id": calendar.id,
            "performance_days": 1,
            "field_days": 1,
            "rejection_days": 1,
            "fen_days": 1,
        }
        if policy:
            policy.write(values)
        else:
            policy = policies.create(dict(values, company_id=company.id))
        assert not policy._configuration_error(lot)
        production = (
            setup["mrp.production"]
            .with_user(user)
            .create(
                {
                    "product_id": product.id,
                    "product_uom_id": product.uom_id.id,
                    "product_qty": 1,
                    "company_id": company.id,
                }
            )
        )
        production.action_confirm()
        production.write({"lot_producing_ids": [Command.set(lot.ids)], "qty_producing": 1})
        assert production.state == "to_close"
        identifiers = {
            "production": production.id,
            "lot": lot.id,
            "actor": user.id,
            "employee": employee.id,
            "company": company.id,
        }
        cursor.commit()
        return identifiers


def _prepare_documents(registry, context, fixture):
    with registry.cursor() as cursor:
        setup = api.Environment(cursor, fixture["actor"], context)
        for kind, key in (("rendimiento", "rnd"), ("terreno", "trn")):
            revision = setup["mc.rov.revision"].create(
                {
                    "lot_id": fixture["lot"],
                    "tipo": kind,
                    "responsable_id": fixture["employee"],
                    "umbilical": "equipo",
                    "largo": 100,
                    "alimentacion": "Generador",
                    "tension_salida": 220,
                    "funcionamiento_continuo_duracion": 1.5,
                    "funcionamiento_continuo_resultado": "ok",
                }
            )
            assert revision.chequeo_ids, "La prueba debe generar su checklist nativo"
            # Los sellos describen la recepción en reparación; RND/TRN no los incluyen.
            assert not revision.inspeccion_ids, "Aceptación no debe crear inspección de sellos"
            revision.chequeo_ids.write({"resultado": "ok"})
            missing = revision._faltantes_para_confirmar(revision)
            assert not missing, (kind, missing)
            fixture[key] = revision.id
        fixture["fen"] = (
            setup["mc.rov.ficha.equipo.nuevo"]
            .create({"lot_id": fixture["lot"], "rnd_id": fixture["rnd"], "trn_id": fixture["trn"]})
            .id
        )
        cursor.commit()


def _state(worker_env, fixture, phase):
    if phase == "manufacture":
        return worker_env["mrp.production"].browse(fixture["production"]).state
    if phase == "select_pair":
        return worker_env["mc.rov.acceptance.activity.automation"]._evidence_summary(
            worker_env["stock.lot"].browse(fixture["lot"])
        )["rnd_id"]
    if phase in ("performance", "field"):
        key = "rnd" if phase == "performance" else "trn"
        return worker_env["mc.rov.revision"].browse(fixture[key]).estado
    return worker_env["mc.rov.ficha.equipo.nuevo"].browse(fixture["fen"]).estado


def _operate(worker_env, fixture, phase):
    if phase == "manufacture":
        worker_env["mrp.production"].browse(fixture["production"]).with_context(
            skip_redirection=True
        ).button_mark_done()
    elif phase == "select_pair":
        worker_env["mc.rov.acceptance.activity.automation"]._select_evidence(
            worker_env["stock.lot"].browse(fixture["lot"]),
            rnd=worker_env["mc.rov.revision"].browse(fixture["rnd"]),
            trn=worker_env["mc.rov.revision"].browse(fixture["trn"]),
        )
    elif phase in ("performance", "field"):
        worker_env["mc.rov.revision"].browse(
            fixture["rnd" if phase == "performance" else "trn"]
        ).action_confirmar()
    elif phase == "emit":
        worker_env["mc.rov.ficha.equipo.nuevo"].browse(fixture["fen"]).action_emitir()
    else:
        raise AssertionError("Unknown concurrency phase")


def _assert_case(
    registry, context, fixture, phase, pending, results
):  # pylint: disable=too-many-arguments
    with registry.cursor() as cursor:
        check = api.Environment(cursor, SUPERUSER_ID, context)
        cycle = check["mc.rov.acceptance.activity.cycle"].search(
            [("production_id", "=", fixture["production"]), ("lot_id", "=", fixture["lot"])]
        )
        assert len(cycle) == 1
        assert check["mrp.production"].browse(fixture["production"]).state == "done"
        runs = check["mc.rov.acceptance.activity.run"].search([("cycle_id", "=", cycle.id)])
        expected_stages = {"performance", "field"}
        if phase in ("field", "emit"):
            expected_stages.add("fen")
        assert set(runs.mapped("stage")) == expected_stages
        assert len(runs) == len(expected_stages) and all(run.occurrence == 1 for run in runs)
        activities = (
            check["mail.activity"]
            .with_context(active_test=False)
            .search([("res_model", "=", "stock.lot"), ("res_id", "=", fixture["lot"])])
        )
        assert set(activities.ids) == set(runs.activity_id.ids), "Orphan activity"
        assert (
            set(runs.filtered(lambda item: item.outcome == "pending").mapped("stage")) == pending
        )
        assert len(activities.filtered("active")) == len(pending)
        assert all(activity.user_id.id == fixture["actor"] for activity in activities)
        assert all(
            run.finished_at and run.finished_by_id.id == fixture["actor"]
            for run in runs
            if run.outcome == "business_done"
        )
        history = check["mc.rov.acceptance.evidence.history"].search([("cycle_id", "=", cycle.id)])
        assert len(history) == (0 if phase == "manufacture" else 2)
        if phase != "manufacture":
            assert cycle.rnd_id.id == fixture["rnd"] and cycle.trn_id.id == fixture["trn"]
        assert cycle.state == ("done" if phase == "emit" else "open")
        if phase == "emit":
            fen = check["mc.rov.ficha.equipo.nuevo"].browse(fixture["fen"])
            assert cycle.fen_id == fen and cycle.closed_at and fen.estado == "emitida"
            assert fen.pdf_attachment_id.raw.startswith(b"%PDF-")
            assert (
                check["ir.attachment"].search_count(
                    [
                        ("res_model", "=", fen._name),
                        ("res_id", "=", fen.id),
                        ("mimetype", "=", "application/pdf"),
                    ]
                )
                == 1
            )
        assert any(item["result"] == "committed" for item in results)
        print(
            "ACCEPTANCE_CONCURRENCY_CASE="
            + json.dumps(
                {
                    "phase": phase,
                    "workers": results,
                    "cycles": len(cycle),
                    "runs": len(runs),
                    "active_pending": len(pending),
                    "evidence_history": len(history),
                    "orphan_activities": 0,
                }
            )
        )


def run_probe(registry, database):
    if not database.startswith("mc_rov_acceptance_ci_"):
        raise AssertionError("Acceptance concurrency requires an isolated CI database")
    context = {
        "tracking_disable": True,
        "mail_create_nosubscribe": True,
        "no_reset_password": True,
        "mail_notify_force_send": False,
    }
    fixture = _fixture(registry, context)
    context["allowed_company_ids"] = [fixture["company"]]

    def race(phase, initial, pending):
        barrier = Barrier(2, timeout=20)

        def worker():
            first_pid, first_state = None, None
            for attempt in range(1, 4):
                seen_state = None
                try:
                    with registry.cursor() as cursor:
                        cursor.execute("SET LOCAL lock_timeout = '30s'")
                        cursor.execute("SET LOCAL statement_timeout = '90s'")
                        worker_env = api.Environment(cursor, fixture["actor"], context)
                        seen_state = _state(worker_env, fixture, phase)
                        if attempt == 1:
                            first_state = seen_state
                            cursor.execute("SELECT pg_backend_pid()")
                            first_pid = cursor.fetchone()[0]
                            barrier.wait()
                        _operate(worker_env, fixture, phase)
                        cursor.commit()
                        return {
                            "attempts": attempt,
                            "pid": first_pid,
                            "read": first_state,
                            "result": "committed",
                        }
                except (SerializationFailure, DeadlockDetected):
                    # Reintentar cursor, entorno y operación completos como una RPC nativa.
                    if attempt == 3:
                        raise
                except UserError as error:
                    # Únicamente aceptar repetición nativa con estado final leído en el retry.
                    final = {"manufacture": "done", "emit": "emitida"}.get(phase)
                    if (
                        not final
                        or attempt == 1
                        or seen_state != final
                        or type(error) is not UserError  # pylint: disable=unidiomatic-typecheck
                    ):
                        raise
                    return {
                        "attempts": attempt,
                        "pid": first_pid,
                        "read": first_state,
                        "result": "native_already_done",
                    }
            raise AssertionError("Unreachable")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker), pool.submit(worker)]
            results = [future.result(timeout=180) for future in futures]
        assert len({item["pid"] for item in results}) == 2
        assert all(item["read"] == initial for item in results), results
        _assert_case(registry, context, fixture, phase, pending, results)

    race("manufacture", "to_close", {"performance", "field"})
    _prepare_documents(registry, context, fixture)
    race("select_pair", False, {"performance", "field"})
    race("performance", "borrador", {"field"})
    race("field", "borrador", {"fen"})
    race("emit", "borrador", set())
    print("ACCEPTANCE_CONCURRENCY_PROBE=PASSED")


# El shell aporta el registro; no confirma su transacción inicial.
shell_env = globals()["env"]
shell_env.cr.rollback()
run_probe(shell_env.registry, shell_env.cr.dbname)
