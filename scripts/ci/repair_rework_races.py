"""Prueba la confirmación de Q3 con dos transacciones simultáneas."""

import concurrent.futures
from threading import Barrier, Event

from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import SUPERUSER_ID, api
from odoo.exceptions import UserError


class RevertRework(Exception):
    """Fuerza la reversión de la primera confirmación."""


def _race(registry, context, case, phase):
    ready = Barrier(2, timeout=20)
    first_write = Event()

    def worker(index):
        for attempt in range(1, 5):
            try:
                with registry.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout='20s'")
                    cursor.execute("SET LOCAL statement_timeout='40s'")
                    env = api.Environment(cursor, case["actors"][index], context)
                    wizard = env["mc.rov.repair.rework.wizard"].browse(case["wizards"][index])
                    if attempt == 1:
                        wizard.read(["line_id", "proposal_id"])
                        cursor.execute("SELECT pg_backend_pid()")
                        pid = cursor.fetchone()[0]
                        ready.wait()
                    if phase in {"replaced", "rollback"} and index == 1:
                        assert first_write.wait(
                            timeout=20
                        ), "La primera operación de Q3 no llegó a escritura"
                    if phase == "replaced" and index == 0:
                        wizard.action_record()
                    else:
                        wizard.action_confirm()
                    if phase == "rollback" and index == 0:
                        first_write.set()
                        raise RevertRework()
                    cursor.commit()
                    if index == 0:
                        first_write.set()
                    return pid, attempt, "committed"
            except RevertRework:
                return pid, attempt, "rolled_back"
            except (SerializationFailure, DeadlockDetected):
                if attempt == 4:
                    raise
            except UserError as error:
                if phase != "replaced" or "La propuesta cambió" not in str(error):
                    raise
                return pid, attempt, "rejected"
        raise AssertionError("Se agotaron los reintentos de Q3")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(worker, index) for index in range(2)]
        return [job.result(timeout=180) for job in jobs]


def _supervisors(registry, context, company):
    # pylint: disable=import-outside-toplevel
    from odoo.tests.common import new_test_user

    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        ids = [
            new_test_user(
                env,
                login=f"qa_q3_race_supervisor_{i}",
                company_id=company,
                groups="stock.group_stock_user,mc_rov.group_repair_rework_supervisor",
            ).id
            for i in range(2)
        ]
        cursor.commit()
    return ids


def _prepare(registry, context, fixture, supervisors, phase):
    # pylint: disable=import-outside-toplevel
    from odoo.addons.mc_rov.tests.test_customer_commitment_browser import prepare_f3_case
    from odoo.addons.mc_rov.tests.test_repair_rework import prepare_q3_order

    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        source = prepare_f3_case(
            env,
            env["stock.warehouse"].browse(fixture["warehouse"]),
            "Q3-" + phase,
            outgoing=False,
        )[0]
        original, line = prepare_q3_order(env, source.product_id, source.lot_id).linea_falla_ids
        env["mc.rov.repair.rework.wizard"].with_user(fixture["users"][0]).create(
            {
                "line_id": line.id,
                "kind": "rework",
                "previous_line_id": original.id,
                "reason": "Prueba de estanqueidad fallida QA Q3",
            }
        ).action_record()
        proposal = (
            env["mc.rov.repair.rework.event"]
            .sudo()
            .search([("line_id", "=", line.id)])
            .ensure_one()
        )
        cases = [fixture["users"][0], supervisors[1]] if phase == "replaced" else supervisors
        case = _confirmations(env["mc.rov.repair.rework.wizard"], line, proposal, cases, phase)
        cursor.commit()
    return case


def _confirmations(model, line, proposal, actors, phase):
    wizards = [
        model.with_user(actor)
        .create(
            {
                "line_id": line.id,
                "proposal_id": proposal.id,
                "kind": "additional" if phase == "replaced" and index == 0 else "rework",
            }
        )
        .id
        for index, actor in enumerate(actors)
    ]
    return {"line": line.id, "proposal": proposal.id, "wizards": wizards, "actors": actors}


def _verify(registry, context, case, phase, workers):
    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        history = env["mc.rov.repair.rework.event"].search([("line_id", "=", case["line"])])
        saved, proposal = history
        assert proposal.id == case["proposal"] and proposal.state == "proposal"
        if phase == "replaced":
            assert saved.state == "additional" and saved.actor_id.id == case["actors"][0]
            assert not saved.proposal_id
        else:
            assert saved.state == "rework" and saved.proposal_id == proposal
            assert (
                saved.previous_line_id == proposal.previous_line_id
                and saved.reason == proposal.reason
            )
            index = case["actors"].index(saved.actor_id.id)
            assert workers[index][2] == "committed"
        return saved.state


def run_repair_rework_races(registry, context, fixture):
    """Comprueba tres carreras y el historial desde una conexión nueva."""
    supervisors = _supervisors(registry, context, fixture["company"])
    reports = []
    for phase, expected in (
        ("duplicate", ["committed", "committed"]),
        ("replaced", ["committed", "rejected"]),
        ("rollback", ["committed", "rolled_back"]),
    ):
        case = _prepare(registry, context, fixture, supervisors, phase)
        workers = _race(registry, context, case, phase)
        assert len({worker[0] for worker in workers}) == 2
        assert sorted(worker[2] for worker in workers) == expected, (phase, workers)
        state = _verify(registry, context, case, phase, workers)
        reports.append(
            {"phase": phase, "workers": workers, "state": state, "history_verified": True}
        )
    return reports
