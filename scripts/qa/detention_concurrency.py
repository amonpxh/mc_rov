"""Ocho carreras F2 en conexiones independientes de una copia privada sin red."""

# Protocolo de evidencia del ejecutor aislado; no es logging del producto.
# Las conexiones propias deben comprometerse para observar carreras reales.
# pylint: disable=unknown-option-value,print-used,too-many-locals,invalid-commit,too-many-arguments

import concurrent.futures
import json
import logging
import re
import sys
from threading import Barrier, Event, local
import time

from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import SUPERUSER_ID, Command, api
from odoo.exceptions import UserError
from odoo.tools import config

# El ejecutor instala este auxiliar propio únicamente en data_dir de la copia.
assert re.fullmatch(r"/var/tmp/mc-rov-detention-races-[A-Za-z0-9]{6}/socket", config["db_host"])
sys.path.insert(0, config["data_dir"])
from detention_retry_log import RetryLogFilter  # pylint: disable=wrong-import-position


RETRY_STATE = local()
CLOSING_RACES = ("start_cancel", "start_stock_done", "start_stock_cancel")


def cancel_source(order):
    """Reparación y Fabricación exponen nombres públicos distintos en Odoo19."""
    if order._name == "repair.order":
        return order.action_repair_cancel()
    assert order._name == "mrp.production"
    return order.action_cancel()


def wait_for_blocker(cr, shared):
    """No libera A hasta que PostgreSQL acredita que B espera su bloqueo."""
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        cr.execute(
            "SELECT %s = ANY(pg_blocking_pids(%s))",
            [shared["pids"][0], shared["pids"][1]],
        )
        if cr.fetchone()[0]:
            return
        shared["pause"].wait(timeout=0.05)
    raise AssertionError("PostgreSQL no acreditó espera antes del rollback")


def fixture(registry):
    """Crea identidades ficticias solo en la base privada ya neutralizada."""
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        assert not env["ir.cron"].search_count([("active", "=", True)])
        category = env["product.category"].create({"name": "QA F2 carreras"})
        env["ir.config_parameter"].set_param("mc_rov.rov_category_id", str(category.id))
        product = env["product.product"].create(
            {"name": "QA F2 carreras", "categ_id": category.id, "tracking": "serial"}
        )
        employee = env["hr.employee"].create({"name": "QA F2 responsable"})
        groups = [
            env.ref(name).id
            for name in (
                "base.group_user",
                "stock.group_stock_user",
                "mrp.group_mrp_user",
            )
        ]
        users = env["res.users"].create(
            [
                {
                    "name": f"QA F2 actor {index}",
                    "login": f"qa_f2_race_{index}",
                    "company_id": env.company.id,
                    "company_ids": [Command.set(env.company.ids)],
                    "group_ids": [Command.set(groups)],
                }
                for index in range(2)
            ]
        )
        result = {
            "product": product.id,
            "employee": employee.id,
            "users": users.ids,
            "company": env.company.id,
        }
        cr.commit()
        return result


def episode(registry, data, model, label):
    """Cada carrera tiene una orden propia y cero historial heredado."""
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        values = {"product_id": data["product"], "company_id": data["company"]}
        if model == "mrp.production":
            values.update(
                product_qty=1,
                product_uom_id=env["product.product"].browse(data["product"]).uom_id.id,
            )
        if model == "repair.order":
            lot = env["stock.lot"].create(
                {"name": "QA-F2-" + label, "product_id": data["product"]}
            )
            values.update(
                lot_id=lot.id,
                tipo_intervencion_ids=[
                    Command.set(env.ref("mc_rov.tipo_reparacion_correctiva").ids)
                ],
            )
        order = env[model].create(values)
        raw = None
        if label.endswith("start_stock_done"):
            component = env["product.product"].create({"name": "QA F2 componente carrera"})
            raw = env["stock.move"].create(
                order._get_move_raw_values(component, 1, component.uom_id)
            )
        if model == "repair.order":
            order.action_validate()
        else:
            order.action_confirm()
        if raw:
            lot = env["stock.lot"].create(
                {"name": "QA-F2-" + label, "product_id": data["product"]}
            )
            order.write({"lot_producing_ids": [Command.set(lot.ids)], "qty_producing": 1})
            raw.write({"quantity": 1, "picked": True})
            raw._action_done()
            finished = order.move_finished_ids.filtered(
                lambda row: row.product_id.id == data["product"]
            )
            finished.write({"lot_ids": [Command.set(lot.ids)], "quantity": 1, "picked": True})
            assert order.state not in ("done", "cancel")
        identity = order.id
        cr.commit()
        return identity


def perform_event(order, service, data, phase, index, shared):
    """Despacha solo los eventos nativos fijos del sondeo."""
    if phase == "finish_pair":
        service.finish_detention(shared["interval"], "QA reanudación")
    elif phase in CLOSING_RACES and index == 1:
        if phase == "start_stock_done":
            order.move_finished_ids._action_done()
        elif phase == "start_stock_cancel":
            order.move_finished_ids.with_context(skip_mo_check=True)._action_cancel()
        else:
            cancel_source(order)
    else:
        service.start_detention(
            order._name,
            order.id,
            "materials",
            data["employee"],
            "QA detención real",
        )


def worker(registry, data, model, source, phase, index, shared):
    """Reintenta la transacción completa con una instantánea nueva, nunca a medias."""
    RETRY_STATE.active = True
    RETRY_STATE.retry_logs = 0
    first_pid = None
    for attempt in range(1, 6):
        try:
            with registry.cursor() as cr:
                env = api.Environment(
                    cr,
                    data["users"][index],
                    {
                        "allowed_company_ids": [data["company"]],
                    },
                )
                cr.execute("SET LOCAL lock_timeout='20s'")
                cr.execute("SELECT pg_backend_pid()")
                pid = cr.fetchone()[0]
                if first_pid is None:
                    first_pid = pid
                    shared["pids"][index] = pid
                order = env[model].browse(source)
                initial_state = order.state
                if attempt == 1:
                    shared["barrier"].wait(timeout=30)
                service = env["mc.rov.detention.service"]
                if phase == "rollback_start" and index == 1:
                    assert shared["inserted"].wait(timeout=30)
                try:
                    perform_event(order, service, data, phase, index, shared)
                except UserError:
                    if phase not in ("start_pair", *CLOSING_RACES) or (
                        phase in CLOSING_RACES and index != 0
                    ):
                        raise
                    cr.rollback()
                    return {
                        "actor": env.uid,
                        "pid": first_pid,
                        "final_pid": pid,
                        "attempts": attempt,
                        "initial_state": initial_state,
                        "result": "blocked",
                        "retry_logs": RETRY_STATE.retry_logs,
                    }
                if phase == "rollback_start" and index == 0:
                    shared["inserted"].set()
                    wait_for_blocker(cr, shared)
                    cr.rollback()
                    return {
                        "actor": env.uid,
                        "pid": first_pid,
                        "final_pid": pid,
                        "attempts": attempt,
                        "initial_state": initial_state,
                        "result": "rolled_back",
                        "rollback_wait_verified": True,
                        "retry_logs": RETRY_STATE.retry_logs,
                    }
                cr.commit()
                return {
                    "actor": env.uid,
                    "pid": first_pid,
                    "final_pid": pid,
                    "attempts": attempt,
                    "initial_state": initial_state,
                    "result": "committed",
                    "retry_logs": RETRY_STATE.retry_logs,
                }
        except (SerializationFailure, DeadlockDetected):
            if attempt == 5:
                raise
    raise AssertionError("Reintentos agotados")


def inspect(registry, data, model, source, phase, workers, original):
    """Comprueba el estado comprometido, autores e identidad tras ambas conexiones."""
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        rows = env["mc.rov.detention.service"].get_intervals(model, source)
        assert len({item["pid"] for item in workers}) == 2
        assert all(item["retry_logs"] <= item["attempts"] - 1 for item in workers)
        assert len({row["id"] for row in rows}) == len(rows)
        outcomes = sorted(item["result"] for item in workers)
        if phase == "start_pair":
            assert outcomes == ["blocked", "committed"] and len(rows) == 1
            assert not rows[0]["ended_at"]
        elif phase == "rollback_start":
            assert workers[0]["rollback_wait_verified"] is True
            assert outcomes == ["committed", "rolled_back"] and len(rows) == 1
            assert rows[0]["actor_id"] == data["users"][1] and not rows[0]["ended_at"]
        elif phase == "finish_pair":
            assert outcomes == ["committed", "committed"] and len(rows) == 1
            assert rows[0]["id"] == original["id"]
            for key in ("started_at", "actor_id", "responsible_employee_id"):
                assert rows[0][key] == original[key]
            assert rows[0]["ended_at"] and rows[0]["end_kind"] == "resumed"
            assert rows[0]["closed_by_id"] in data["users"]
        else:
            assert phase in CLOSING_RACES and env[model].browse(source).state == (
                "done" if phase == "start_stock_done" else "cancel"
            )
            assert workers[1]["result"] == "committed" and len(rows) in (0, 1)
            for row in rows:
                assert row["ended_at"] and row["end_kind"] == "source_closed"
                assert row["closed_by_id"] == data["users"][1]
        for row in rows:
            assert row["responsible_employee_id"] == data["employee"]
            assert row["actor_id"] in data["users"]
            assert not row["ended_at"] or row["ended_at"] >= row["started_at"]
        if phase == "start_pair":
            winner = next(item for item in workers if item["result"] == "committed")
            assert rows[0]["actor_id"] == winner["actor"]
        return {
            "model": model,
            "phase": phase,
            "workers": workers,
            "intervals": len(rows),
            "pending": sum(not row["ended_at"] for row in rows),
            "identity_actor_chronology_verified": True,
        }


def run(registry):
    """No recibe modelos, IDs, acciones ni código del cliente SSH."""
    retry_filter = RetryLogFilter(RETRY_STATE, (SerializationFailure, DeadlockDetected))
    logging.getLogger("odoo.sql_db").addFilter(retry_filter)
    data = fixture(registry)
    for model in ("repair.order", "mrp.production"):
        phases = ("start_pair", "finish_pair", "start_cancel", "rollback_start")
        if model == "mrp.production":
            phases += ("start_stock_done", "start_stock_cancel")
        for phase in phases:
            source = episode(registry, data, model, model.replace(".", "-") + phase)
            shared = {
                "barrier": Barrier(2),
                "inserted": Event(),
                "pause": Event(),
                "pids": {},
            }
            original = None
            if phase == "finish_pair":
                with registry.cursor() as cr:
                    actor = api.Environment(cr, data["users"][0], {})
                    service = actor["mc.rov.detention.service"]
                    shared["interval"] = service.start_detention(
                        model, source, "materials", data["employee"], "QA inicio"
                    )
                    original = service.get_intervals(model, source)[0]
                    cr.commit()
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(worker, registry, data, model, source, phase, index, shared)
                    for index in range(2)
                ]
                workers = [future.result(timeout=90) for future in futures]
            result = inspect(registry, data, model, source, phase, workers, original)
            print("DETENTION_RACE_CASE=" + json.dumps(result, sort_keys=True), flush=True)
    print("DETENTION_RACE_PROBE=PASSED", flush=True)


shell_env = globals()["env"]
assert re.fullmatch(r"mc_rov_detention_races_[A-Za-z0-9]{6}", shell_env.cr.dbname)
shell_env.cr.rollback()
run(shell_env.registry)
