"""Datos persistidos únicamente en una copia aislada y neutralizada de STAGING."""

import concurrent.futures
import json
from threading import Barrier

from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import SUPERUSER_ID, Command, api, fields


def _fixture(registry, context):  # pylint: disable=too-many-locals
    with registry.cursor() as cursor:
        test_env = api.Environment(cursor, SUPERUSER_ID, context)
        assert not test_env["ir.cron"].search_count([("active", "=", True)])
        assert not test_env["ir.mail_server"].search_count([("active", "=", True)])
        company = test_env.company
        category = test_env["product.category"].create({"name": "QA Calidad concurrente"})
        test_env["ir.config_parameter"].set_param("mc_rov.rov_category_id", str(category.id))
        product = test_env["product.product"].create(
            {"name": "QA equipo Calidad concurrente", "categ_id": category.id}
        )
        users = []
        for role, group in (
            ("taller", "quality.group_quality_user"),
            ("supervisor", "quality.group_quality_manager"),
        ):
            users.append(
                test_env["res.users"].create(
                    {
                        "name": "QA Calidad concurrente " + role,
                        "login": "qa_quality_concurrent_" + role,
                        "company_id": company.id,
                        "company_ids": [Command.set(company.ids)],
                        "group_ids": [
                            Command.set(
                                [
                                    test_env.ref("base.group_user").id,
                                    test_env.ref(group).id,
                                    test_env.ref("stock.group_stock_user").id,
                                ]
                            )
                        ],
                    }
                )
            )
        recipient = users[0]
        actor = users[1]
        calendar = test_env["resource.calendar"].create(
            {
                "name": "QA Calidad concurrente lunes a viernes",
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
        policies = test_env["mc.rov.quality.activity.policy"]
        policy = policies.search([("company_id", "=", company.id)], limit=1)
        values = {
            "enabled": False,
            "user_id": recipient.id,
            "calendar_id": calendar.id,
            "employee_id": False,
            "lead_days": 1,
        }
        if policy:
            policy.write(values)
        else:
            policy = policies.create(dict(values, company_id=company.id))
        control = test_env["mc.rov.automation.control"].search(
            [("company_id", "=", company.id)], limit=1
        )
        if control:
            control.enabled = True
        team = test_env["quality.alert.team"].create(
            {"name": "QA Calidad concurrente", "company_id": company.id}
        )
        opened = test_env["quality.alert.stage"].create(
            {"name": "QA abierta concurrente", "done": False}
        )
        closed = test_env["quality.alert.stage"].create(
            {"name": "QA cerrada concurrente", "done": True}
        )
        alert = test_env["quality.alert"].create(
            {
                "name": "QA alerta concurrente",
                "company_id": company.id,
                "team_id": team.id,
                "stage_id": opened.id,
                "product_id": product.id,
                "product_tmpl_id": product.product_tmpl_id.id,
            }
        )
        assert not test_env["mc.rov.quality.activity.run"].search_count(
            [("alert_id", "=", alert.id)]
        )
        policy.enabled = True
        assert not policy._configuration_error(alert)
        identifiers = {
            "alert": alert.id,
            "opened": opened.id,
            "closed": closed.id,
            "actor": actor.id,
            "recipient": recipient.id,
            "company": company.id,
        }
        cursor.commit()
        return identifiers


def _assert_case(registry, context, fixture, expected, results):
    phase, cycles, pending = expected
    with registry.cursor() as cursor:
        check_env = api.Environment(cursor, SUPERUSER_ID, context)
        alert = check_env["quality.alert"].browse(fixture["alert"])
        runs = check_env["mc.rov.quality.activity.run"].search(
            [("alert_id", "=", alert.id)], order="cycle,id"
        )
        activities = (
            check_env["mail.activity"]
            .with_context(active_test=False)
            .search([("res_model", "=", "quality.alert"), ("res_id", "=", alert.id)])
        )
        active = activities.filtered("active")
        assert len(runs) == cycles and runs.mapped("cycle") == list(range(1, cycles + 1))
        assert len(runs.filtered(lambda run: run.outcome == "pending")) == pending
        assert len(active) == pending
        assert set(activities.ids) == set(runs.activity_id.ids), "Orphan activity"
        assert all(
            run.finished_at and run.finished_by_id.id == fixture["actor"]
            for run in runs
            if run.outcome == "business_done"
        )
        assert bool(alert.stage_id.done) == (not pending)
        if active:
            assert active.user_id.id == fixture["recipient"]
        print(
            "QUALITY_CONCURRENCY_CASE="
            + json.dumps(
                {
                    "phase": phase,
                    "workers": results,
                    "cycles": len(runs),
                    "activities": len(activities),
                    "active_pending": len(active),
                    "orphan_activities": 0,
                }
            )
        )


def run_probe(registry, database):
    if not database.startswith("mc_rov_quality_ci_"):
        raise AssertionError("Quality concurrency requires an isolated CI database")
    context = {
        "tracking_disable": True,
        "mail_create_nosubscribe": True,
        "no_reset_password": True,
        "mail_notify_force_send": False,
    }
    fixture = _fixture(registry, context)
    context["allowed_company_ids"] = [fixture["company"]]

    def race(phase, was_closed, cycles, pending):
        barrier = Barrier(2, timeout=15)

        def worker(index):
            first_pid, first_state = None, None
            for attempt in range(1, 4):
                try:
                    with registry.cursor() as cursor:
                        cursor.execute("SET LOCAL lock_timeout = '15s'")
                        cursor.execute("SET LOCAL statement_timeout = '30s'")
                        worker_env = api.Environment(cursor, fixture["actor"], context)
                        alert = worker_env["quality.alert"].browse(fixture["alert"])
                        if attempt == 1:
                            first_state = bool(alert.stage_id.done)
                            cursor.execute("SELECT pg_backend_pid()")
                            first_pid = cursor.fetchone()[0]
                            barrier.wait()
                        if phase == "start":
                            worker_env["mc.rov.quality.activity.automation"]._start(
                                alert, fields.Datetime.now()
                            )
                        elif phase in ("close", "reopen"):
                            alert.write(
                                {"stage_id": fixture["closed" if phase == "close" else "opened"]}
                            )
                        elif phase in ("stage_close", "stage_reopen"):
                            worker_env["quality.alert.stage"].browse(fixture["opened"]).write(
                                {"done": phase == "stage_close"}
                            )
                        elif phase == "mixed_close":
                            if index:
                                worker_env["quality.alert.stage"].browse(fixture["opened"]).write(
                                    {"done": True}
                                )
                            else:
                                alert.write({"stage_id": fixture["closed"]})
                        else:
                            raise AssertionError("Unknown race phase")
                        cursor.commit()
                        return {
                            "attempts": attempt,
                            "pid": first_pid,
                            "read_closed": first_state,
                            "result": "committed",
                        }
                except (SerializationFailure, DeadlockDetected):
                    # Reintentar cursor, entorno y operación completos como en una RPC de Odoo.
                    if attempt == 3:
                        raise
            raise AssertionError("Unreachable")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, index) for index in range(2)]
            results = [future.result(timeout=60) for future in futures]
        assert len({item["pid"] for item in results}) == 2
        assert all(item["read_closed"] == was_closed for item in results), results
        _assert_case(registry, context, fixture, (phase, cycles, pending), results)

    race("start", False, 1, 1)
    race("close", False, 1, 0)
    race("reopen", True, 2, 1)
    race("stage_close", False, 2, 0)
    race("stage_reopen", True, 3, 1)
    race("mixed_close", False, 3, 0)
    print("QUALITY_CONCURRENCY_PROBE=PASSED")


# La transacción inicial del shell nunca se confirma.
shell_env = globals()["env"]
shell_env.cr.rollback()
run_probe(shell_env.registry, shell_env.cr.dbname)
