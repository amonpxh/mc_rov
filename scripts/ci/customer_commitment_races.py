"""Carreras F3 con transacciones independientes en la copia efímera de CI."""

import concurrent.futures
from datetime import timedelta
from threading import Barrier, Event

from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import SUPERUSER_ID, Command, api, fields
from odoo.exceptions import UserError


class RollbackProbe(Exception):
    """Revierte una constancia ya creada en la transacción del actor."""


def _race(registry, context, actors, wizard_ref, phase):
    model, ids = wizard_ref
    barrier = Barrier(2, timeout=20)
    before_rollback = Event()

    def worker(index):
        for attempt in range(1, 5):
            try:
                with registry.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout='20s'")
                    cursor.execute("SET LOCAL statement_timeout='45s'")
                    env = api.Environment(cursor, actors[index], context)
                    wizard = env[model].browse(ids[index])
                    if attempt == 1:
                        wizard.read(["id"])
                        cursor.execute("SELECT pg_backend_pid()")
                        pid = cursor.fetchone()[0]
                        barrier.wait()
                    if phase == "dispatch_rollback" and index == 1:
                        assert before_rollback.wait(timeout=20), "El primer actor no registró"
                    wizard.action_apply()
                    if phase == "dispatch_rollback" and index == 0:
                        # El segundo ya tomó su instantánea, pero aún no registró la salida.
                        before_rollback.set()
                        raise RollbackProbe()
                    cursor.commit()
                    return pid, attempt, "committed"
            except RollbackProbe:
                return pid, attempt, "rolled_back"
            except (DeadlockDetected, SerializationFailure):
                if attempt == 4:
                    raise
            except UserError as error:
                expected_message = {
                    "original_conflict": "Ya existe una promesa original.",
                    "dispatch_duplicate": "La constancia cambió.",
                    "dispatch_correct_invalidate": "La constancia cambió.",
                }.get(phase)
                if not expected_message or expected_message not in str(error):
                    raise
                return pid, attempt, "rejected_stale"
        raise AssertionError("Reintentos agotados")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, index) for index in range(2)]
        workers = [future.result(timeout=180) for future in futures]
    assert len({item[0] for item in workers}) == 2
    expected = (
        ["committed", "rolled_back"]
        if phase == "dispatch_rollback"
        else (
            ["committed", "rejected_stale"]
            if phase in {"original_conflict", "dispatch_duplicate", "dispatch_correct_invalidate"}
            else ["committed", "committed"]
        )
    )
    assert sorted(item[2] for item in workers) == expected, (phase, workers)
    return workers


def _promise_wizards(repair, actors, now, phase, promise_wizard):
    if phase == "change_repeat":
        promise_wizard(repair.with_user(actors[0]), now).action_apply()
        changes = {
            "operation": "reprogram",
            "agreed_at": now - timedelta(days=1),
            "reason": "Cambio concurrente QA F3",
        }
    else:
        changes = {}
    return [
        promise_wizard(
            repair.with_user(actor),
            now,
            **(
                {"evidence": "Acuerdo alternativo QA F3"}
                if phase == "original_conflict" and index
                else changes
            ),
        )
        for index, actor in enumerate(actors)
    ]


def _dispatch_wizards(case, actors, now, phase, dispatch_wizard):
    repair, picking, attachment = case
    if phase == "dispatch_correct_invalidate":
        original = dispatch_wizard(picking.with_user(actors[0]), repair, attachment, now)
        original.action_apply()
        correction = dispatch_wizard(picking.with_user(actors[0]), repair, attachment, now)
        correction.reason = "Corrección QA F3"
        source = picking.with_user(actors[1])
        action = source.action_open_customer_dispatch_invalidation()
        invalidation = source.env[action["res_model"]].browse(action["res_id"])
        invalidation.reason = "Invalidación QA F3"
        return [correction, invalidation]
    return [dispatch_wizard(picking.with_user(actor), repair, attachment, now) for actor in actors]


def _check_history(env, phase, source, winners, expected_date):
    """Lee desde una tercera conexión y compara con la identidad del ganador."""
    winner_ids = [actor for _index, actor in winners]
    if not phase.startswith("dispatch"):
        promise = env["mc.rov.customer.commitment"].search([("repair_id", "=", source)])
        assert len(promise) == 1 and promise.promised_date == expected_date
        assert promise.actor_id.id in winner_ids
        changes = promise.change_ids
        assert len(changes) == int(phase == "change_repeat")
        if changes:
            assert changes.kind == "reprogram" and changes.actor_id.id in winner_ids
        return len(promise) + len(changes)
    events = env["mc.rov.customer.dispatch"].search([("picking_id", "=", source)], order="id")
    assert len(events) == (2 if phase == "dispatch_correct_invalidate" else 1)
    assert events[0].kind == "confirmed" and events[0].effective_date == expected_date
    assert events[-1].actor_id.id in winner_ids
    if len(events) == 2:
        assert events[-1].previous_id == events[0]
        assert events[-1].kind == ("corrected" if winners[0][0] == 0 else "invalidated")
    return len(events)


def run_customer_commitment_races(registry, context, fixture, results):
    """Comprueba seis conflictos y conserva evidencia sin datos de negocio."""
    # El registro Odoo ya contiene los modelos y las utilidades del módulo.
    # pylint: disable=import-outside-toplevel,too-many-locals
    from odoo.addons.mc_rov.models.production_kpi_metrics import local_day
    from odoo.addons.mc_rov.tests.test_customer_commitment_browser import (
        dispatch_wizard,
        prepare_f3_case,
        promise_wizard,
    )

    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        actors = env["res.users"].browse(fixture["users"])
        actors.write(
            {
                "group_ids": [
                    Command.link(env.ref("mc_rov.group_customer_commitment_supervisor").id),
                    Command.link(env.ref("stock.group_stock_manager").id),
                ]
            }
        )
        actors = actors.ids
        cursor.commit()
    now = fields.Datetime.now()
    for phase in (
        "original_repeat",
        "original_conflict",
        "change_repeat",
        "dispatch_duplicate",
        "dispatch_correct_invalidate",
        "dispatch_rollback",
    ):
        outgoing = phase.startswith("dispatch")
        with registry.cursor() as cursor:
            env = api.Environment(cursor, SUPERUSER_ID, context)
            warehouse = env["stock.warehouse"].browse(fixture["warehouse"])
            repair, picking, attachment = prepare_f3_case(env, warehouse, phase, outgoing=outgoing)
            wizards = (
                _dispatch_wizards(
                    (repair, picking, attachment), actors, now, phase, dispatch_wizard
                )
                if outgoing
                else _promise_wizards(repair, actors, now, phase, promise_wizard)
            )
            model, ids = wizards[0]._name, [wizard.id for wizard in wizards]
            source = picking.id if outgoing else repair.id
            cursor.commit()
        workers = _race(registry, context, actors, (model, ids), phase)
        winners = [
            (index, actors[index])
            for index, worker in enumerate(workers)
            if worker[2] == "committed"
        ]
        with registry.cursor() as cursor:
            env = api.Environment(cursor, SUPERUSER_ID, context)
            events = _check_history(env, phase, source, winners, local_day(now))
        results.append(
            {"phase": phase, "workers": workers, "events": events, "actor_verified": True}
        )
