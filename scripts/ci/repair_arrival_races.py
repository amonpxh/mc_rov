"""Comprueba la atribución de llegadas F6 en una copia del runner."""

import concurrent.futures
from datetime import timedelta
from threading import Barrier, Event

from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import SUPERUSER_ID, api
from odoo.exceptions import UserError


class RevertArrival(Exception):
    """Fuerza rollback después de capturar la llegada."""


def _race(registry, context, actors, wizard_ids, phase):
    barrier = Barrier(2, timeout=20)
    captured = Event()

    def worker(index):
        for attempt in range(1, 5):
            try:
                with registry.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout='20s'")
                    cursor.execute("SET LOCAL statement_timeout='40s'")
                    env = api.Environment(cursor, actors[index], context)
                    wizard = env["mc.rov.repair.arrival.wizard"].browse(wizard_ids[index])
                    if attempt == 1:
                        wizard.read(["repair_id", "picking_id"])
                        cursor.execute("SELECT pg_backend_pid()")
                        pid = cursor.fetchone()[0]
                        barrier.wait()
                    if phase == "rollback" and index == 1:
                        assert captured.wait(timeout=20), "El primer actor no llegó a capturar"
                    wizard.action_apply()
                    if phase == "rollback" and index == 0:
                        captured.set()
                        raise RevertArrival()
                    cursor.commit()
                    return pid, attempt, "committed"
            except RevertArrival:
                return pid, attempt, "rolled_back"
            except (SerializationFailure, DeadlockDetected):
                if attempt == 4:
                    raise
            except UserError as exc:
                if phase not in {"timing_conflict", "shared_receipt"}:
                    raise
                if "ya tiene evidencia registrada" not in str(exc):
                    raise
                return pid, attempt, "rejected"
        raise AssertionError("Se agotaron los reintentos de F6")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        pending = [pool.submit(worker, index) for index in range(2)]
        workers = [job.result(timeout=180) for job in pending]
    return workers


def run_repair_arrival_races(registry, context, fixture, reports):
    """Ejecuta cuatro carreras y comprueba el ledger desde una tercera conexión."""
    # Las utilidades de prueba requieren que el registro del módulo esté cargado.
    # pylint: disable=import-outside-toplevel,too-many-locals
    from odoo.addons.mc_rov.tests.test_customer_commitment_browser import prepare_f3_case
    from odoo.addons.mc_rov.tests.test_repair_lead_time import arrival_wizard, receive_rov

    actors = fixture["users"]
    for phase, expected in (
        ("duplicate", ["committed", "committed"]),
        ("timing_conflict", ["committed", "rejected"]),
        ("shared_receipt", ["committed", "rejected"]),
        ("rollback", ["committed", "rolled_back"]),
    ):
        with registry.cursor() as cursor:
            env = api.Environment(cursor, SUPERUSER_ID, context)
            warehouse = env["stock.warehouse"].browse(fixture["warehouse"])
            repair, _outgoing, _attachment = prepare_f3_case(env, warehouse, phase, outgoing=False)
            receipt = receive_rov(env, warehouse, repair)
            other = repair
            if phase == "shared_receipt":
                other = env["repair.order"].create(
                    {
                        "company_id": repair.company_id.id,
                        "partner_id": repair.partner_id.id,
                        "product_id": repair.product_id.id,
                        "product_uom": repair.product_uom.id,
                        "lot_id": repair.lot_id.id,
                    }
                )
            actual = receipt.date_done - timedelta(days=2)
            delayed = {
                "delayed": True,
                "arrived_at": actual,
                "reason": "Validación posterior QA F6",
            }
            first = arrival_wizard(repair.with_user(actors[0]), receipt)
            second = arrival_wizard(
                other.with_user(actors[1]),
                receipt,
                **(delayed if phase in {"timing_conflict", "rollback"} else {}),
            )
            wizard_ids = [first.id, second.id]
            visits = [repair.id, other.id]
            picking_id, lot_id, validated = receipt.id, repair.lot_id.id, receipt.date_done
            cursor.commit()
        workers = _race(registry, context, actors, wizard_ids, phase)
        assert len({worker[0] for worker in workers}) == 2
        assert sorted(worker[2] for worker in workers) == expected, (phase, workers)
        with registry.cursor() as cursor:
            env = api.Environment(cursor, SUPERUSER_ID, context)
            evidence = (
                env["mc.rov.repair.arrival"].search([("repair_id", "in", visits)]).ensure_one()
            )
            index = actors.index(evidence.actor_id.id)
            assert workers[index][2] == "committed"
            assert evidence.repair_id.id == visits[index]
            assert (evidence.picking_id.id, evidence.lot_id.id) == (picking_id, lot_id)
            assert evidence.validated_at == validated
            late_winner = index == 1 and phase in {"timing_conflict", "rollback"}
            assert evidence.arrived_at == (actual if late_winner else validated)
            assert evidence.reason == (delayed["reason"] if late_winner else False)
        reports.append(
            {
                "phase": phase,
                "workers": workers,
                "arrivals": 1,
                "actor_verified": True,
                "arrival_and_validation_verified": True,
            }
        )
