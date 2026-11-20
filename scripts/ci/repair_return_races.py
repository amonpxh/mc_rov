"""Comprueba la unicidad del vínculo y el dictamen de retorno en PostgreSQL."""

import concurrent.futures
from threading import Barrier, Event

from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import SUPERUSER_ID, api
from odoo.exceptions import UserError


class RevertReturn(Exception):
    """Revierte un dictamen para comprobar que el segundo se conserva."""


def _race(registry, context, actors, wizards, phase):
    barrier = Barrier(2, timeout=20)
    written = Event()

    def worker(index):
        for attempt in range(1, 5):
            try:
                with registry.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout='20s'")
                    cursor.execute("SET LOCAL statement_timeout='40s'")
                    env = api.Environment(cursor, actors[index], context)
                    wizard = env["mc.rov.repair.return.wizard"].browse(wizards[index])
                    if attempt == 1:
                        wizard.read(["return_id", "relation"])
                        cursor.execute("SELECT pg_backend_pid()")
                        pid = cursor.fetchone()[0]
                        barrier.wait()
                    if phase == "rollback" and index == 1:
                        assert written.wait(timeout=20), "El primer actor no llegó a dictaminar"
                    if phase == "duplicate_link":
                        wizard.action_link()
                    else:
                        wizard.action_decide()
                    if phase == "rollback" and index == 0:
                        written.set()
                        raise RevertReturn()
                    cursor.commit()
                    return pid, attempt, "committed"
            except RevertReturn:
                return pid, attempt, "rolled_back"
            except (SerializationFailure, DeadlockDetected):
                if attempt == 4:
                    raise
            except UserError as exc:
                if phase != "opposite_verdicts" or "ya tiene un dictamen registrado" not in str(
                    exc
                ):
                    raise
                return pid, attempt, "rejected"
        raise AssertionError("Se agotaron los reintentos de Q2")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(worker, index) for index in range(2)]
        return [job.result(timeout=180) for job in jobs]


def _supervisors(registry, context, company):
    # El auxiliar nativo de Odoo solo se carga tras abrir el registro de la copia.
    # pylint: disable=import-outside-toplevel
    from odoo.tests.common import new_test_user

    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        actors = [
            new_test_user(
                env,
                login=f"qa_q2_race_supervisor_{index}",
                company_id=company,
                groups="stock.group_stock_user,mc_rov.group_repair_return_supervisor,"
                "mc_rov.group_customer_commitment_supervisor",
            ).id
            for index in range(2)
        ]
        cursor.commit()
    return actors


def _decisions(model, returned_id, supervisors, phase):
    actors = [supervisors[0], supervisors[0]] if phase == "duplicate_verdict" else supervisors
    submissions = [
        {"relation": "confirmed", "reason": "Falla relacionada QA Q2"},
        {"relation": "unrelated", "reason": "Causa distinta QA Q2"},
    ]
    if phase == "duplicate_verdict":
        submissions[1] = submissions[0]
    wizards = [
        model.with_user(actor).create({"return_id": returned_id, **values}).id
        for actor, values in zip(actors, submissions)
    ]
    return {"actors": actors, "wizards": wizards, "submissions": submissions}


def _prepare(registry, context, fixture, supervisors, phase):
    # pylint: disable=import-outside-toplevel
    from odoo.addons.mc_rov.tests.test_repair_returns import prepare_q2_case

    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        workshop = env["res.users"].browse(fixture["users"][0])
        original, returned = prepare_q2_case(
            env,
            env["stock.warehouse"].browse(fixture["warehouse"]),
            phase,
            workshop,
            env["res.users"].browse(supervisors[0]),
        )
        model = env["mc.rov.repair.return.wizard"]
        link = {"return_id": returned.id, "original_id": original.id}
        first = model.with_user(workshop).create(link)
        case = {
            "original": original.id,
            "returned": returned.id,
            "lot": original.lot_id.id,
            "linker": workshop.id,
        }
        if phase == "duplicate_link":
            case.update(
                actors=fixture["users"],
                wizards=[first.id, model.with_user(fixture["users"][1]).create(link).id],
            )
        else:
            first.action_link()
            case.update(_decisions(model, returned.id, supervisors, phase))
        cursor.commit()
    return case


def _verify(registry, context, case, phase, workers):
    committed = [index for index, worker in enumerate(workers) if worker[2] == "committed"]
    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        row = (
            env["mc.rov.repair.return"].search([("return_id", "=", case["returned"])]).ensure_one()
        )
        assert row.original_id.id == case["original"]
        assert row.lot_id.id == case["lot"]
        assert row.arrival_id.repair_id == row.return_id
        assert row.original_id in row.dispatch_id.repair_ids
        if phase == "duplicate_link":
            assert row.linked_by.id in [case["actors"][index] for index in committed]
            assert row.relation == "pending" and not (
                row.decided_by or row.decided_at or row.reason
            )
            return row.relation
        assert row.linked_by.id == case["linker"]
        winner = committed[0]
        assert (row.relation, row.reason) == (
            case["submissions"][winner]["relation"],
            case["submissions"][winner]["reason"],
        )
        assert row.decided_by.id == case["actors"][winner] and row.decided_at
        return row.relation


def run_repair_return_races(registry, context, fixture):
    """Ejecuta cuatro carreras y verifica su evidencia desde una tercera conexión."""
    supervisors = _supervisors(registry, context, fixture["company"])
    reports = []
    for phase, expected in (
        ("duplicate_link", ["committed", "committed"]),
        ("duplicate_verdict", ["committed", "committed"]),
        ("opposite_verdicts", ["committed", "rejected"]),
        ("rollback", ["committed", "rolled_back"]),
    ):
        case = _prepare(registry, context, fixture, supervisors, phase)
        workers = _race(registry, context, case["actors"], case["wizards"], phase)
        assert len({worker[0] for worker in workers}) == 2
        assert sorted(worker[2] for worker in workers) == expected, (phase, workers)
        relation = _verify(registry, context, case, phase, workers)
        reports.append(
            {
                "phase": phase,
                "workers": workers,
                "links": 1,
                "relation": relation,
                "evidence_and_actors_verified": True,
            }
        )
    return reports
