"""Committed fixtures are permitted only in this private, neutralized database clone."""

import concurrent.futures
import json
from threading import Barrier

from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import SUPERUSER_ID, Command, api


def _create_fixture(registry, context):
    with registry.cursor() as cursor:
        test_env = api.Environment(cursor, SUPERUSER_ID, context)
        assert (
            not test_env["ir.cron"]
            .with_context(active_test=False)
            .search_count([("active", "=", True)])
        )
        company = test_env.company
        category = test_env["product.category"].create({"name": "QA concurrent ROV"})
        test_env["ir.config_parameter"].set_param("mc_rov.rov_category_id", str(category.id))
        product = test_env["product.product"].create(
            {"name": "QA concurrent ROV", "tracking": "serial", "categ_id": category.id}
        )
        lot = test_env["stock.lot"].create(
            {"name": "QA-CONCURRENT-001", "product_id": product.id, "company_id": company.id}
        )
        assert lot.es_un_rov
        user = test_env["res.users"].create(
            {
                "name": "QA concurrent recipient",
                "login": "qa_repair_concurrent_recipient",
                "company_id": company.id,
                "company_ids": [Command.set(company.ids)],
                "group_ids": [
                    Command.set(
                        [
                            test_env.ref("base.group_user").id,
                            test_env.ref("stock.group_stock_user").id,
                        ]
                    )
                ],
            }
        )
        calendar = test_env["resource.calendar"].create(
            {
                "name": "QA concurrent calendar",
                "company_id": company.id,
                "tz": "America/Santiago",
                "attendance_ids": [
                    Command.clear(),
                    *[
                        Command.create(
                            {
                                "name": "QA",
                                "dayofweek": str(day),
                                "hour_from": 8,
                                "hour_to": 17,
                                "day_period": "morning",
                            }
                        )
                        for day in range(5)
                    ],
                ],
            }
        )
        policies = test_env["mc.rov.repair.activity.policy"]
        policy = policies.search([("company_id", "=", company.id)])
        values = {
            "enabled": True,
            "user_id": user.id,
            "employee_id": False,
            "calendar_id": calendar.id,
            "diagnosis_days": 2,
            "repair_days": 2,
        }
        if policy:
            policy.write(values)
        else:
            policy = policies.create(dict(values, company_id=company.id))
        order = test_env["repair.order"].create(
            {"product_id": product.id, "lot_id": lot.id, "company_id": company.id}
        )
        assert not policy._configuration_error(order)
        order_id = order.id
        cursor.commit()
        return order_id


def run_probe(registry, database):
    if not database.startswith("mc_rov_repair_ci_"):
        raise AssertionError("Concurrency fixtures require an isolated repair CI database")
    context = {
        "tracking_disable": True,
        "mail_create_nosubscribe": True,
        "no_reset_password": True,
    }
    order_id = _create_fixture(registry, context)

    def race(state, expected_stages):
        barrier = Barrier(2, timeout=15)

        def worker():
            first_pid = None
            first_state = None
            for attempt in range(1, 4):
                try:
                    with registry.cursor() as cursor:
                        cursor.execute("SET LOCAL lock_timeout = '15s'")
                        cursor.execute("SET LOCAL statement_timeout = '30s'")
                        worker_env = api.Environment(cursor, SUPERUSER_ID, context)
                        order = worker_env["repair.order"].browse(order_id)
                        if attempt == 1:
                            first_state = order.state
                            cursor.execute("SELECT pg_backend_pid()")
                            first_pid = cursor.fetchone()[0]
                            barrier.wait()
                        order.write({"state": state})
                        cursor.commit()
                        return {"attempts": attempt, "pid": first_pid, "read": first_state}
                except (SerializationFailure, DeadlockDetected):
                    # HTTP/RPC similarly retries a complete transaction with a fresh snapshot.
                    if attempt == 3:
                        raise
            raise AssertionError("Unreachable")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker), pool.submit(worker)]
            results = [future.result(timeout=60) for future in futures]
        assert len({item["pid"] for item in results}) == 2, results
        expected_read = "draft" if state == "confirmed" else "confirmed"
        assert all(item["read"] == expected_read for item in results), results
        with registry.cursor() as cursor:
            check_env = api.Environment(cursor, SUPERUSER_ID, context)
            order = check_env["repair.order"].browse(order_id)
            runs = check_env["mc.rov.repair.activity.run"].search([("repair_id", "=", order_id)])
            activities = (
                check_env["mail.activity"]
                .with_context(active_test=False)
                .search([("res_model", "=", "repair.order"), ("res_id", "=", order_id)])
            )
            assert order.state == state and order.mc_activity_cycle == 1
            assert sorted(runs.mapped("stage")) == sorted(expected_stages), runs.ids
            assert all(run.cycle == 1 and run.outcome == "pending" for run in runs)
            assert set(activities.ids) == set(runs.mapped("activity_id").ids)
            assert len(activities) == len(expected_stages)
            print(
                "REPAIR_CONCURRENCY_CASE="
                + json.dumps(
                    {
                        "state": state,
                        "workers": results,
                        "runs": len(runs),
                        "activities": len(activities),
                        "orphan_activities": 0,
                    }
                )
            )

    race("confirmed", ["diagnosis"])
    race("under_repair", ["diagnosis", "repair"])
    print("REPAIR_CONCURRENCY_PROBE=PASSED")


# Odoo shell supplies env; never commit its startup transaction or use a live database.
shell_env = globals()["env"]
shell_env.cr.rollback()
run_probe(shell_env.registry, shell_env.cr.dbname)
