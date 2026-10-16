"""Fixtures persistidas solo en la copia neutralizada de concurrencia."""

import concurrent.futures
import json
from threading import Barrier

from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import SUPERUSER_ID, Command, api
from odoo.exceptions import UserError


def _configure_policy(test_env, user, calendar):
    company = user.company_id
    policies = test_env["mc.rov.manufacturing.activity.policy"]
    policy = policies.search([("company_id", "=", company.id)])
    values = {
        "enabled": True,
        "user_id": user.id,
        "employee_id": False,
        "calendar_id": calendar.id,
        "lead_days": 28,
    }
    if policy:
        policy.write(values)
    else:
        policy = policies.create(dict(values, company_id=company.id))
    controls = test_env["mc.rov.automation.control"]
    control = controls.search([("company_id", "=", company.id)])
    if control:
        control.enabled = True
    return policy


def _create_fixture(registry, context):
    with registry.cursor() as cursor:
        test_env = api.Environment(cursor, SUPERUSER_ID, context)
        assert not test_env["ir.cron"].search_count([("active", "=", True)])
        assert not test_env["ir.mail_server"].search_count([("active", "=", True)])
        company = test_env.company
        category = test_env["product.category"].create({"name": "QA fabricación concurrente"})
        test_env["ir.config_parameter"].set_param("mc_rov.rov_category_id", str(category.id))
        product = test_env["product.product"].create(
            {"name": "QA fabricación concurrente", "tracking": "serial", "categ_id": category.id}
        )
        lot = test_env["stock.lot"].create(
            {
                "name": "QA-MANUFACTURING-CONCURRENT",
                "product_id": product.id,
                "company_id": company.id,
            }
        )
        user = test_env["res.users"].create(
            {
                "name": "QA Taller concurrente",
                "login": "qa_manufacturing_concurrent_recipient",
                "company_id": company.id,
                "company_ids": [Command.set(company.ids)],
                "group_ids": [
                    Command.set(
                        [test_env.ref("base.group_user").id, test_env.ref("mrp.group_mrp_user").id]
                    )
                ],
            }
        )
        calendar = test_env["resource.calendar"].create(
            {
                "name": "QA fabricación días corridos",
                "company_id": company.id,
                "tz": "America/Santiago",
                "attendance_ids": [Command.clear()],
            }
        )
        policy = _configure_policy(test_env, user, calendar)
        production = (
            test_env["mrp.production"]
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
        assert not policy._configuration_error(production)
        identifiers = production.id, lot.id, user.id, company.id
        cursor.commit()
        return identifiers


def _assert_case(registry, context, fixture, stage, results):
    production_id, _lot_id, user_id, _company_id = fixture
    with registry.cursor() as cursor:
        check_env = api.Environment(cursor, SUPERUSER_ID, context)
        production = check_env["mrp.production"].browse(production_id)
        runs = check_env["mc.rov.manufacturing.activity.run"].search(
            [("production_id", "=", production_id)]
        )
        activities = (
            check_env["mail.activity"]
            .with_context(active_test=False)
            .search([("res_model", "=", "mrp.production"), ("res_id", "=", production_id)])
        )
        assert production.state == stage
        assert len(runs) == 1 and runs.cycle == 1
        assert runs.outcome == ("pending" if stage == "confirmed" else "business_done")
        assert set(activities.ids) == set(runs.activity_id.ids), "Orphan activity"
        active = activities.filtered("active")
        assert len(active) == (1 if stage == "confirmed" else 0)
        if stage == "done":
            assert runs.finished_by_id.id == user_id and runs.finished_at
            assert sum(item["result"] == "committed" for item in results) >= 1
        print(
            "MANUFACTURING_CONCURRENCY_CASE="
            + json.dumps(
                {
                    "state": stage,
                    "workers": results,
                    "runs": len(runs),
                    "activities": len(activities),
                    "active_pending": len(active),
                    "orphan_activities": 0,
                }
            )
        )


def run_probe(registry, database):
    if not database.startswith("mc_rov_manufacturing_ci_"):
        raise AssertionError("Concurrency fixtures require an isolated manufacturing CI database")
    context = {
        "tracking_disable": True,
        "mail_create_nosubscribe": True,
        "no_reset_password": True,
        "mail_notify_force_send": False,
    }
    fixture = _create_fixture(registry, context)
    production_id, lot_id, user_id, company_id = fixture
    context["allowed_company_ids"] = [company_id]

    def race(stage):
        barrier = Barrier(2, timeout=15)

        def worker():
            first_pid, first_state = None, None
            for attempt in range(1, 4):
                seen_state = None
                try:
                    with registry.cursor() as cursor:
                        cursor.execute("SET LOCAL lock_timeout = '15s'")
                        cursor.execute("SET LOCAL statement_timeout = '30s'")
                        worker_env = api.Environment(cursor, user_id, context)
                        production = worker_env["mrp.production"].browse(production_id)
                        seen_state = production.state
                        if attempt == 1:
                            first_state = seen_state
                            cursor.execute("SELECT pg_backend_pid()")
                            first_pid = cursor.fetchone()[0]
                            barrier.wait()
                        if stage == "confirmed":
                            production.action_confirm()
                        else:
                            production.with_context(skip_redirection=True).button_mark_done()
                        cursor.commit()
                        return {
                            "attempts": attempt,
                            "pid": first_pid,
                            "read": first_state,
                            "result": "committed",
                        }
                except (SerializationFailure, DeadlockDetected):
                    # Reintentar la transacción completa, como el servicio RPC de Odoo.
                    if attempt == 3:
                        raise
                except UserError as error:
                    # Tras terminar, MRP puede rechazar repetir la fabricación de esa serie.
                    # Solo aceptar esa validación nativa con el estado done leído de nuevo.
                    if (
                        stage != "done"
                        or seen_state != "done"
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
            results = [future.result(timeout=60) for future in futures]
        assert len({item["pid"] for item in results}) == 2, results
        assert all(
            item["read"] == ("draft" if stage == "confirmed" else "to_close") for item in results
        )
        _assert_case(registry, context, fixture, stage, results)

    race("confirmed")
    with registry.cursor() as cursor:
        setup_env = api.Environment(cursor, user_id, context)
        production = setup_env["mrp.production"].browse(production_id)
        production.write({"lot_producing_ids": [Command.set([lot_id])], "qty_producing": 1})
        assert production.state == "to_close"
        cursor.commit()
    race("done")
    print("MANUFACTURING_CONCURRENCY_PROBE=PASSED")


# El shell solo aporta el registro: su transacción inicial nunca se confirma.
shell_env = globals()["env"]
shell_env.cr.rollback()
run_probe(shell_env.registry, shell_env.cr.dbname)
