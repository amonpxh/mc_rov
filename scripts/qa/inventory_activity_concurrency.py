"""Carreras nativas de stock en una copia neutralizada, con dos conexiones reales."""

# stdout es el protocolo del verificador, no logging de producto.
# pylint: disable=unknown-option-value,print-used,too-many-locals,too-many-statements
import concurrent.futures
import json
from datetime import timedelta
from threading import Barrier

from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import SUPERUSER_ID, Command, api, fields


def _fixture(registry, context):
    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        assert not env["ir.cron"].search_count([("active", "=", True)])
        assert not env["ir.mail_server"].search_count([("active", "=", True)])
        assert (
            env["ir.config_parameter"].get_param("web.base.url")
            == "http://127.0.0.1/isolated-concurrency"
        )
        company = env.company
        users = []
        for index, timezone in enumerate(("UTC", "Asia/Tokyo")):
            users.append(
                env["res.users"].create(
                    {
                        "name": "QA Inventario concurrente " + str(index),
                        "login": "qa_inventory_concurrency_" + str(index),
                        "company_id": company.id,
                        "company_ids": [Command.set(company.ids)],
                        "tz": timezone,
                        "group_ids": [
                            Command.set(
                                [
                                    env.ref("base.group_user").id,
                                    env.ref("stock.group_stock_user").id,
                                ]
                            )
                        ],
                    }
                )
            )
        calendar = env["resource.calendar"].create(
            {
                "name": "QA Inventario concurrente Santiago",
                "company_id": company.id,
                "tz": "America/Santiago",
                "attendance_ids": [
                    Command.clear(),
                    *[
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
                ],
            }
        )
        locations = {}
        for name, usage in [
            ("supplier", "supplier"),
            ("stock", "internal"),
            ("other", "internal"),
            ("customer", "customer"),
        ]:
            locations[name] = env["stock.location"].create(
                {
                    "name": "QA Inventario carrera " + name,
                    "usage": usage,
                    "company_id": company.id if usage == "internal" else False,
                }
            )
        category = env["product.category"].create({"name": "QA Inventario carrera independiente"})
        product = env["product.product"].create(
            {
                "name": "QA Inventario carrera",
                "type": "consu",
                "is_storable": True,
                "company_id": company.id,
                "categ_id": category.id,
            }
        )
        env["stock.quant"]._update_available_quantity(product, locations["stock"], 20)
        policy = env["mc.rov.inventory.activity.policy"].create(
            {
                "company_id": company.id,
                "enabled": True,
                "calendar_id": calendar.id,
                "lead_days": 3,
            }
        )
        control = env["mc.rov.automation.control"].search(
            [("company_id", "=", company.id)], limit=1
        )
        if control:
            control.enabled = True
        else:
            env["mc.rov.automation.control"].create({"company_id": company.id, "enabled": True})
        scheduled = fields.Datetime.now() + timedelta(days=7)
        pickings = {}
        for code, src, dst in [
            ("incoming", "supplier", "stock"),
            ("outgoing", "stock", "customer"),
            ("internal", "stock", "other"),
        ]:
            kind = env["stock.picking.type"].create(
                {
                    "name": "QA Inventario carrera " + code,
                    "code": code,
                    "sequence_code": "QAIC" + code.upper(),
                    "warehouse_id": False,
                    "company_id": company.id,
                    "default_location_src_id": locations[src].id,
                    "default_location_dest_id": locations[dst].id,
                    "create_backorder": "ask",
                }
            )
            env["mc.rov.inventory.activity.rule"].create(
                {
                    "policy_id": policy.id,
                    "picking_type_id": kind.id,
                    "user_id": users[0].id,
                }
            )
            picking = env["stock.picking"].create(
                {
                    "picking_type_id": kind.id,
                    "company_id": company.id,
                    "location_id": locations[src].id,
                    "location_dest_id": locations[dst].id,
                    "scheduled_date": scheduled,
                    "move_ids": [
                        Command.create(
                            {
                                "product_id": product.id,
                                "product_uom_qty": 2,
                                "product_uom": product.uom_id.id,
                                "location_id": locations[src].id,
                                "location_dest_id": locations[dst].id,
                            }
                        )
                    ],
                }
            )
            assert picking.state == "draft"
            if code != "incoming":
                picking.with_user(users[0]).action_confirm()
            pickings[code] = picking.id
        cursor.commit()
        return {"company": company.id, "users": [user.id for user in users], "pickings": pickings}


def _validate(picking, quantity):
    for move in picking.move_ids.filtered(lambda row: row.state not in ("done", "cancel")):
        move.write({"quantity": quantity, "picked": True})
    result = picking.button_validate()
    if isinstance(result, dict) and result.get("res_model") == "stock.backorder.confirmation":
        assert quantity == 1, result
        picking.env["stock.backorder.confirmation"].with_context(
            **result.get("context", {})
        ).create(
            {
                "pick_ids": [Command.set(picking.ids)],
                "backorder_confirmation_line_ids": [
                    Command.create({"picking_id": picking.id, "to_backorder": True})
                ],
            }
        ).process()
    else:
        assert result is True, result
    assert picking.state == "done"


def _race(registry, context, fixture, phase, picking_id):
    barrier = Barrier(2, timeout=15)

    def worker(index):
        first_pid, first_read = None, None
        for attempt in range(1, 4):
            try:
                with registry.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout = '15s'")
                    cursor.execute("SET LOCAL statement_timeout = '30s'")
                    env = api.Environment(cursor, fixture["users"][index], context)
                    picking = env["stock.picking"].browse(picking_id)
                    if attempt == 1:
                        first_read = picking.state
                        cursor.execute("SELECT pg_backend_pid()")
                        first_pid = cursor.fetchone()[0]
                        barrier.wait()
                    result = "committed"
                    if phase in ("confirm", "duplicate_confirm"):
                        picking.action_confirm()
                    elif phase == "cancel":
                        picking.action_cancel()
                    elif picking.state == "done":
                        result = "native_already_done"
                    else:
                        _validate(picking, 1 if phase in ("partial", "remaining") else 2)
                    cursor.commit()
                    return {
                        "attempts": attempt,
                        "pid": first_pid,
                        "read": first_read,
                        "result": result,
                    }
            except (SerializationFailure, DeadlockDetected):
                # RPCs concurrentes deben repetir la transacción entera con caché nueva.
                if attempt == 3:
                    raise
        raise AssertionError("Unreachable")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            future.result(timeout=90) for future in [pool.submit(worker, i) for i in range(2)]
        ]
    assert len({row["pid"] for row in results}) == 2
    assert results[0]["read"] == results[1]["read"]
    return results


def _check(
    registry, context, fixture, picking_id, phase, workers
):  # pylint: disable=too-many-arguments
    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        picking = env["stock.picking"].browse(picking_id)
        remaining = env["stock.picking"].search([("backorder_id", "=", picking.id)])
        assert len(remaining) == (1 if phase == "partial" else 0), (phase, remaining.ids)
        ids = (picking | remaining).ids
        cycles = env["mc.rov.inventory.activity.cycle"].search([("picking_id", "in", ids)])
        runs = env["mc.rov.inventory.activity.run"].search([("picking_id", "in", ids)])
        types = env["mail.activity.type"].browse(
            [
                env.ref("mc_rov.activity_type_inventory_" + key).id
                for key in ("receipt", "delivery", "transfer")
            ]
        )
        activities = (
            env["mail.activity"]
            .with_context(active_test=False)
            .search(
                [
                    ("res_model", "=", "stock.picking"),
                    ("res_id", "in", ids),
                    ("activity_type_id", "in", types.ids),
                ]
            )
        )
        pending = runs.filtered(lambda row: row.outcome == "pending")
        active = activities.filtered("active")
        expected_pending = 1 if phase in ("confirm", "duplicate_confirm", "partial") else 0
        assert len(cycles) == len(runs) == len(ids)
        assert len({(run.cycle_id.id, run.event) for run in runs}) == len(runs)
        assert len(active) == len(pending) == expected_pending
        assert set(activities.ids) == set(runs.activity_id.ids), "Orphan activity"
        assert set(active.ids) == set(pending.activity_id.ids)
        for cycle in cycles:
            assert cycle.lead_days == 3 and cycle.deadline_tz == "America/Santiago"
            assert cycle.current_deadline == cycle.original_deadline
            if cycle.parent_id:
                assert cycle.parent_id.picking_id == cycle.picking_id.backorder_id
                assert cycle.original_deadline == cycle.parent_id.original_deadline
                assert cycle.current_deadline == cycle.parent_id.current_deadline
                assert cycle.anchor_at == cycle.parent_id.anchor_at
            else:
                assert cycle.anchor_at == max(cycle.confirmed_at, cycle.scheduled_at_initial)
                assert cycle.scheduled_at_initial > cycle.confirmed_at
                assert cycle.original_deadline == cycle.policy_id._deadline(
                    cycle.confirmed_at, cycle.scheduled_at_initial, cycle.native_deadline_initial
                )
        for run in runs:
            assert run.original_deadline == run.current_deadline == run.cycle_id.current_deadline
            if run.outcome != "pending":
                assert (
                    run.finished_at
                    and run.finished_by_id.id in fixture["users"]
                    and run.finish_reason
                )
        assert all(
            a.user_id.id == fixture["users"][0]
            and a.date_deadline
            == pending.filtered(
                lambda row, activity=a: row.activity_id == activity
            ).current_deadline
            for a in active
        )
        if phase in ("confirm", "duplicate_confirm"):
            assert picking.state in ("confirmed", "waiting", "assigned")
        elif phase == "cancel":
            assert picking.state == "cancel" and runs.outcome == "cancelled"
        else:
            assert picking.state == "done"
            assert sum(picking.move_ids.mapped("quantity")) == (
                1 if phase in ("partial", "remaining") else 2
            )
            assert runs.filtered(lambda row: row.picking_id == picking).outcome == "business_done"
        if remaining:
            assert remaining.state in ("confirmed", "waiting", "assigned")
            assert sum(remaining.move_ids.mapped("product_uom_qty")) == 1
        print(
            "INVENTORY_CONCURRENCY_CASE="
            + json.dumps(
                {
                    "phase": phase,
                    "workers": workers,
                    "cycles": len(cycles),
                    "runs": len(runs),
                    "active_pending": len(active),
                    "orphan_activities": 0,
                    "deadline_preserved": True,
                    "remaining_orders": len(remaining),
                    "operation_code": picking.picking_type_id.code,
                }
            )
        )
        return remaining.id if remaining else False


def run_probe(registry, database):
    assert database.startswith("mc_rov_inventory_ci_")
    context = {
        "no_reset_password": True,
        "mail_create_nosubscribe": True,
        "tracking_disable": True,
    }
    fixture = _fixture(registry, context)
    context["allowed_company_ids"] = [fixture["company"]]
    receipt = fixture["pickings"]["incoming"]
    for phase in ("confirm", "duplicate_confirm", "validate"):
        _check(
            registry,
            context,
            fixture,
            receipt,
            phase,
            _race(registry, context, fixture, phase, receipt),
        )
    outgoing = fixture["pickings"]["outgoing"]
    _check(
        registry,
        context,
        fixture,
        outgoing,
        "cancel",
        _race(registry, context, fixture, "cancel", outgoing),
    )
    internal = fixture["pickings"]["internal"]
    remaining = _check(
        registry,
        context,
        fixture,
        internal,
        "partial",
        _race(registry, context, fixture, "partial", internal),
    )
    _check(
        registry,
        context,
        fixture,
        remaining,
        "remaining",
        _race(registry, context, fixture, "remaining", remaining),
    )
    print("INVENTORY_CONCURRENCY_DEADLINES=PASSED")
    print("INVENTORY_CONCURRENCY_PROBE=PASSED")


shell_env = globals()["env"]
shell_env.cr.rollback()
run_probe(shell_env.registry, shell_env.cr.dbname)
