"""Cierres genéricos, operación real y reprogramación en conexiones independientes."""

# El instalador aporta las dos funciones del fixture de stock ya versionado.
# stdout es un protocolo de evidencia, no logging del producto.
# pylint: disable=unknown-option-value,print-used,too-many-locals,too-many-statements
import concurrent.futures
import json
from datetime import timedelta
from threading import Barrier, Event

from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import SUPERUSER_ID, Command, api, fields
from odoo.exceptions import UserError


class ProbeRollback(Exception):
    """Fallo deliberado tras el cierre real para demostrar su reversión completa."""


def _new_receipt(registry, context, fixture, template_id):
    with registry.cursor() as cursor:
        env = api.Environment(cursor, fixture["users"][0], context)
        template = env["stock.picking"].browse(template_id)
        move = template.move_ids.ensure_one()
        picking = env["stock.picking"].create(
            {
                "picking_type_id": template.picking_type_id.id,
                "company_id": template.company_id.id,
                "location_id": template.location_id.id,
                "location_dest_id": template.location_dest_id.id,
                "scheduled_date": fields.Datetime.now() + timedelta(days=7),
                "move_ids": [
                    Command.create(
                        {
                            "product_id": move.product_id.id,
                            "product_uom_qty": 2,
                            "product_uom": move.product_uom.id,
                            "location_id": template.location_id.id,
                            "location_dest_id": template.location_dest_id.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        cursor.commit()
        return picking.id


def _snapshot(registry, context, picking_id):
    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        picking = env["stock.picking"].browse(picking_id)
        run = env["mc.rov.inventory.activity.run"].search([("picking_id", "=", picking_id)])
        run.ensure_one()
        assert run.outcome == "pending" and run.activity_id.active
        return {
            "picking": picking_id,
            "state": picking.state,
            "run": run.id,
            "activity": run.activity_id.id,
            "kind": run.activity_id.activity_type_id.id,
            "original": run.original_deadline,
            "current": run.current_deadline,
            "moves": picking.move_ids.read(["state", "quantity", "product_uom_qty", "picked"]),
        }


def _is_closed(env, snapshot):
    run = env["mc.rov.inventory.activity.run"].sudo().browse(snapshot["run"])
    run.invalidate_recordset()
    return run.outcome != "pending"


def _race_completion(registry, context, fixture, snapshot, phase):
    barrier = Barrier(2, timeout=15)
    changed, other_started = Event(), Event()
    validate = globals()["native_inventory"]["validate"]

    # Mantener los cuatro órdenes en el mismo arnés hace comparables los reintentos.
    def worker(index):  # pylint: disable=too-many-branches
        first_pid, first_state = None, None
        for attempt in range(1, 4):
            try:
                with registry.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout = '15s'")
                    cursor.execute("SET LOCAL statement_timeout = '30s'")
                    actor = fixture["users"][0 if phase == "generic_pair" else index]
                    env = api.Environment(cursor, actor, context)
                    picking = env["stock.picking"].browse(snapshot["picking"])
                    activity = env["mail.activity"].browse(snapshot["activity"])
                    if attempt == 1:
                        first_state = picking.state
                        cursor.execute("SELECT pg_backend_pid()")
                        first_pid = cursor.fetchone()[0]
                        barrier.wait()
                    result = "committed"
                    if phase == "generic_pair" or (index == 0 and phase == "generic_vs_real"):
                        if not activity.exists() or not activity.active:
                            assert _is_closed(env, snapshot)
                            result = "already_closed"
                        else:
                            try:
                                with cursor.savepoint():
                                    if phase == "generic_pair" and index == 1:
                                        activity.action_cancel()
                                    else:
                                        activity.action_feedback(feedback="QA cierre genérico")
                            except UserError as error:
                                assert error.__class__ is UserError
                                assert "trabajo automático pendiente" in str(error)
                                result = "blocked"
                            else:
                                # Si ganó el cierre real, su resultado nunca pasa a manual_done.
                                assert _is_closed(env, snapshot)
                                result = "already_closed"
                    elif index == 0 and phase == "reprogram_vs_real":
                        if not activity.exists() or not activity.active:
                            assert _is_closed(env, snapshot)
                            result = "already_closed"
                        else:
                            try:
                                with cursor.savepoint():
                                    env["mc.rov.activity.assignment.wizard"].create(
                                        {
                                            "activity_ids": [Command.set(activity.ids)],
                                            "apply_deadline": True,
                                            "date_deadline": snapshot["current"]
                                            + timedelta(days=2),
                                            "reason": "QA compromiso concurrente autorizado",
                                        }
                                    ).action_apply()
                            except UserError:
                                assert _is_closed(env, snapshot)
                                result = "already_closed"
                            else:
                                result = "reprogrammed"
                    elif index == 0 and phase == "rollback_vs_real":
                        try:
                            with cursor.savepoint():
                                assert picking.state != "done"
                                validate(picking, 2)
                                assert _is_closed(env, snapshot)
                                changed.set()
                                assert other_started.wait(15)
                                raise ProbeRollback()
                        except ProbeRollback:
                            cursor.rollback()
                            return {
                                "pid": first_pid,
                                "attempts": attempt,
                                "read": first_state,
                                "result": "rolled_back",
                            }
                    else:
                        if phase == "rollback_vs_real":
                            assert changed.wait(15)
                            other_started.set()
                        if picking.state == "done":
                            result = "already_closed"
                        else:
                            validate(picking, 2)
                    cursor.commit()
                    return {
                        "pid": first_pid,
                        "attempts": attempt,
                        "read": first_state,
                        "result": result,
                    }
            except (SerializationFailure, DeadlockDetected):
                if attempt == 3:
                    raise
        raise AssertionError("Unreachable")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, index) for index in range(2)]
        results = [future.result(timeout=100) for future in futures]
    assert len({row["pid"] for row in results}) == 2
    assert results[0]["read"] == results[1]["read"] == snapshot["state"]
    return results


def _check_completion(
    registry, context, fixture, snapshot, phase, workers
):  # pylint: disable=too-many-arguments
    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        picking = env["stock.picking"].browse(snapshot["picking"])
        runs = env["mc.rov.inventory.activity.run"].search([("picking_id", "=", picking.id)])
        assert runs.ids == [snapshot["run"]]
        cycle = runs.cycle_id
        assert len(cycle) == 1
        activities = (
            env["mail.activity"]
            .with_context(active_test=False)
            .search(
                [
                    ("res_model", "=", "stock.picking"),
                    ("res_id", "=", picking.id),
                    ("activity_type_id", "=", snapshot["kind"]),
                ]
            )
        )
        assert set(activities.ids) == set(runs.activity_id.ids)
        pending = runs.filtered(lambda row: row.outcome == "pending")
        assert set(activities.filtered("active").ids) == set(pending.activity_id.ids)
        assert runs.original_deadline == cycle.original_deadline == snapshot["original"]
        assert runs.current_deadline == cycle.current_deadline
        allowed = {snapshot["current"]}
        if phase == "reprogram_vs_real":
            allowed.add(snapshot["current"] + timedelta(days=2))
        assert runs.current_deadline in allowed
        if phase == "generic_pair":
            assert [row["result"] for row in workers] == ["blocked", "blocked"]
            assert runs.outcome == "pending" and picking.state == snapshot["state"]
            assert not runs.finished_at and not runs.finished_by_id and not runs.finish_reason
            assert (
                picking.move_ids.read(["state", "quantity", "product_uom_qty", "picked"])
                == snapshot["moves"]
            )
            assert runs.activity_id.date_deadline == snapshot["current"]
        else:
            assert picking.state == "done" and runs.outcome == "business_done"
            assert not pending
            assert runs.finished_by_id.id == fixture["users"][1]
            assert runs.finished_at and runs.finish_reason
            assert sum(picking.move_ids.mapped("quantity")) == 2
            assert workers[1]["result"] == "committed"
            if phase == "rollback_vs_real":
                assert workers[0]["result"] == "rolled_back"
            elif phase == "generic_vs_real":
                assert workers[0]["result"] in ("blocked", "already_closed")
            else:
                assert workers[0]["result"] in ("reprogrammed", "already_closed")
        print(
            "AUTOMATIC_RACE_CASE="
            + json.dumps(
                {
                    "phase": phase,
                    "workers": workers,
                    "runs": len(runs),
                    "cycles": len(cycle),
                    "active_pending": len(pending),
                    "outcome": runs.outcome,
                    "orphan_activities": 0,
                    "original_deadline_preserved": True,
                    "final_deadline_consistent": True,
                    "business_actor_verified": phase != "generic_pair",
                }
            )
        )


def run_probe(registry, database):
    assert database.startswith("mc_rov_auto_close_ci_")
    context = {
        "no_reset_password": True,
        "mail_create_nosubscribe": True,
        "tracking_disable": True,
        "mail_notify_force_send": False,
    }
    fixture = globals()["native_inventory"]["fixture"](registry, context)
    context["allowed_company_ids"] = [fixture["company"]]
    receipt = fixture["pickings"]["incoming"]
    with registry.cursor() as cursor:
        setup = api.Environment(cursor, SUPERUSER_ID, context)
        # Solo la cuenta ficticia de esta copia obtiene coordinación para la carrera.
        setup["res.users"].browse(fixture["users"][0]).write(
            {"group_ids": [Command.link(setup.ref("mc_rov.group_work_assignment_coordinate").id)]}
        )
        setup["stock.picking"].browse(receipt).with_user(fixture["users"][0]).action_confirm()
        cursor.commit()
    for phase in ("generic_pair", "generic_vs_real", "reprogram_vs_real", "rollback_vs_real"):
        if phase in ("reprogram_vs_real", "rollback_vs_real"):
            receipt = _new_receipt(registry, context, fixture, receipt)
        snapshot = _snapshot(registry, context, receipt)
        workers = _race_completion(registry, context, fixture, snapshot, phase)
        _check_completion(registry, context, fixture, snapshot, phase, workers)
    print("AUTOMATIC_RACE_PROBE=PASSED")


shell_env = globals()["env"]
shell_env.cr.rollback()
run_probe(shell_env.registry, shell_env.cr.dbname)
