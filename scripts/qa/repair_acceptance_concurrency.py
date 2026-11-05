"""Formal repair attempts in two independent transactions on a neutralized clone."""

# stdout is the evidence protocol consumed by the isolated runner.
# pylint: disable=unknown-option-value,print-used,too-many-locals
import concurrent.futures
import json
from threading import Barrier

from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import SUPERUSER_ID, Command, api
from odoo.exceptions import UserError


class ProbeRollback(Exception):
    """Deliberate rollback after native confirmation, before its transaction commits."""


def _fixture(registry, context):
    with registry.cursor() as cursor:
        setup = api.Environment(cursor, SUPERUSER_ID, context)
        assert not setup["ir.cron"].search_count([("active", "=", True)])
        assert not setup["ir.mail_server"].search_count([("active", "=", True)])
        assert setup["ir.config_parameter"].get_param("mc_rov.entorno") == "STAGING"
        assert (
            setup["ir.config_parameter"].get_param("web.base.url")
            == "http://127.0.0.1/isolated-concurrency"
        )
        category = setup["product.category"].create({"name": "QA final repair concurrency"})
        setup["ir.config_parameter"].set_param("mc_rov.rov_category_id", str(category.id))
        product = setup["product.product"].create(
            {"name": "QA final repair product", "tracking": "serial", "categ_id": category.id}
        )
        employee = setup["hr.employee"].create({"name": "QA final repair technician"})
        users = []
        for index in range(2):
            user = setup["res.users"].create(
                {
                    "name": f"QA final repair actor {index}",
                    "login": f"qa_final_repair_concurrency_{index}",
                    "company_id": setup.company.id,
                    "company_ids": [Command.set(setup.company.ids)],
                    "group_ids": [
                        Command.set(
                            [
                                setup.ref("base.group_user").id,
                                setup.ref("stock.group_stock_user").id,
                                setup.ref("mc_rov.group_work_assignment_team").id,
                            ]
                        )
                    ],
                }
            )
            users.append(user.id)
        fixture = {
            "company": setup.company.id,
            "product": product.id,
            "employee": employee.id,
            "users": users,
        }
        cursor.commit()
        return fixture


def _new_episode(registry, context, fixture, label):
    complete = label != "abort_pair"
    second = label == "competing_revisions"
    with registry.cursor() as cursor:
        setup = api.Environment(cursor, SUPERUSER_ID, context)
        product = setup["product.product"].browse(fixture["product"])
        lot = setup["stock.lot"].create(
            {
                "name": "QA-FINAL-" + label,
                "product_id": product.id,
                "company_id": fixture["company"],
            }
        )
        repair = setup["repair.order"].create(
            {
                "product_id": product.id,
                "product_qty": 1,
                "product_uom": product.uom_id.id,
                "lot_id": lot.id,
                "company_id": fixture["company"],
            }
        )
        revisions = []
        for _index in range(2 if second else 1):
            revision = setup["mc.rov.revision"].create(
                {
                    "lot_id": lot.id,
                    "responsable_id": fixture["employee"],
                    "repair_id": repair.id,
                    "tipo": "reparacion",
                    "motivo": "otro",
                    "mc_acceptance_purpose": "final",
                    "mc_correction_required": "no",
                    "mc_retest_required": "no",
                }
            )
            assert revision.chequeo_ids, "Native repair checklist must exist"
            if complete:
                revision.write(
                    {
                        "umbilical": "equipo",
                        "largo": 100,
                        "alimentacion": "Generador",
                        "tension_salida": 220,
                        "funcionamiento_continuo_duracion": 1.5,
                        "funcionamiento_continuo_resultado": "ok",
                    }
                )
                revision.chequeo_ids.write({"resultado": "ok"})
                revision.inspeccion_ids.write({"estado_sello": "intacto"})
            else:
                revision.chequeo_ids[0].resultado = "no_ok"
            revisions.append(revision.id)
        cursor.commit()
        return {"repair": repair.id, "lot": lot.id, "revisions": revisions}


def _start(registry, context, fixture, episode):
    with registry.cursor() as cursor:
        actor = api.Environment(cursor, fixture["users"][0], context)
        actor["mc.rov.revision"].browse(episode["revisions"][0]).action_start_final_acceptance()
        cursor.commit()


def _race(registry, context, fixture, episode, phase):
    barrier = Barrier(2, timeout=20)

    def worker(index):  # pylint: disable=too-many-branches
        first_pid, first_read = None, None
        for retry in range(1, 5):
            try:
                with registry.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout = '20s'")
                    cursor.execute("SET LOCAL statement_timeout = '45s'")
                    actor = api.Environment(cursor, fixture["users"][index], context)
                    revision_id = episode["revisions"][
                        index if phase == "competing_revisions" else 0
                    ]
                    revision = actor["mc.rov.revision"].browse(revision_id)
                    if retry == 1:
                        first_read = {
                            "state": revision.estado,
                            "purpose": revision.mc_acceptance_purpose,
                        }
                        cursor.execute("SELECT pg_backend_pid()")
                        first_pid = cursor.fetchone()[0]
                        barrier.wait()
                    result = "committed"
                    try:
                        with cursor.savepoint():
                            if phase in ("start_pair", "competing_revisions", "restart_pair"):
                                revision.action_start_final_acceptance()
                            elif phase == "identity_vs_start":
                                if index == 0:
                                    revision.action_start_final_acceptance()
                                else:
                                    revision.write({"mc_acceptance_purpose": "diagnostic"})
                            elif phase == "abort_pair":
                                revision.action_abort_final_acceptance("QA fallo concurrente")
                            elif phase in ("confirm_pair", "rollback_vs_confirm"):
                                revision.action_confirmar()
                                if phase == "rollback_vs_confirm" and index == 0:
                                    raise ProbeRollback()
                            else:
                                raise AssertionError("Unknown phase")
                    except UserError as error:
                        assert error.__class__ is UserError
                        allowed = {
                            "competing_revisions": ("Otra revisión tiene un intento pendiente",),
                            "identity_vs_start": (
                                "Solo una revisión final en borrador",
                                "La identidad de la aceptación final",
                            ),
                        }
                        assert any(
                            message in str(error) for message in allowed.get(phase, ())
                        ), str(error)
                        result = "blocked"
                    cursor.commit()
                    return {
                        "pid": first_pid,
                        "read": first_read,
                        "attempts": retry,
                        "actor": actor.uid,
                        "result": result,
                    }
            except ProbeRollback:
                return {
                    "pid": first_pid,
                    "read": first_read,
                    "attempts": retry,
                    "actor": fixture["users"][index],
                    "result": "rolled_back",
                }
            except (SerializationFailure, DeadlockDetected):
                if retry == 4:
                    raise
        raise AssertionError("Retries exhausted")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, index) for index in range(2)]
        return [future.result(timeout=150) for future in futures]


def _check(registry, context, fixture, episode, case):
    phase, workers = case["phase"], case["workers"]
    with registry.cursor() as cursor:
        check = api.Environment(cursor, SUPERUSER_ID, context)
        attempts = check["mc.rov.repair.acceptance.attempt"].search(
            [("repair_id", "=", episode["repair"])], order="ordinal"
        )
        revision = check["mc.rov.revision"].browse(episode["revisions"][0])
        pending = attempts.filtered(lambda row: row.state == "pending")
        assert len(pending) <= 1
        assert attempts.mapped("ordinal") == list(range(1, len(attempts) + 1))
        assert all(
            row.repair_id.exists()
            and row.revision_id.exists()
            and row.lot_id.exists()
            and row.company_id.id == fixture["company"]
            and row.lot_id.id == episode["lot"]
            and row.revision_id.repair_id == row.repair_id
            for row in attempts
        )
        for row in attempts.filtered(lambda row: row.state != "pending"):
            assert row.closed_at and row.actor_id.id in fixture["users"]
            assert row.requirements_snapshot.get("configuration")
            assert row.requirements_snapshot.get("evidence")
            assert bool(row.confirmed_at) == (row.state == "confirmed")
        if phase in ("start_pair", "competing_revisions"):
            assert len(attempts) == len(pending) == 1
        elif phase in ("confirm_pair", "rollback_vs_confirm"):
            assert len(attempts) == 1 and not pending
            assert attempts.state == "confirmed" and revision.estado == "confirmado"
            if phase == "rollback_vs_confirm":
                assert attempts.actor_id.id == fixture["users"][1]
        elif phase == "abort_pair":
            assert len(attempts) == 1 and attempts.state == "aborted"
            assert attempts.verdict_snapshot == "rechazado" and revision.estado == "borrador"
        elif phase == "restart_pair":
            assert len(attempts) == 2 and not pending
            assert attempts.mapped("state") == ["aborted", "confirmed"]
            assert attempts.mapped("verdict_snapshot") == ["rechazado", "aprobado"]
        elif phase == "identity_vs_start":
            assert (len(attempts) == 1 and revision.mc_acceptance_purpose == "final") or (
                not attempts and revision.mc_acceptance_purpose == "diagnostic"
            )
        print(
            "REPAIR_ACCEPTANCE_RACE_CASE="
            + json.dumps(
                {
                    "phase": phase,
                    "workers": workers,
                    "attempts": len(attempts),
                    "pending": len(pending),
                    "states": attempts.mapped("state"),
                    "verdicts": attempts.mapped("verdict_snapshot"),
                    "ordinals": attempts.mapped("ordinal"),
                    "orphan_attempts": 0,
                    "revision_state": revision.estado,
                    "purpose": revision.mc_acceptance_purpose,
                    "actor_verified": phase == "rollback_vs_confirm",
                }
            )
        )


def run_probe(registry, database):
    if not database.startswith("mc_rov_repair_acceptance_ci_"):
        raise AssertionError("Final repair concurrency requires its isolated database")
    context = {
        "tracking_disable": True,
        "mail_create_nosubscribe": True,
        "no_reset_password": True,
        "mail_notify_force_send": False,
        "lang": "en_US",
    }
    fixture = _fixture(registry, context)
    context["allowed_company_ids"] = [fixture["company"]]
    for phase in (
        "start_pair",
        "competing_revisions",
        "confirm_pair",
        "abort_pair",
        "rollback_vs_confirm",
        "identity_vs_start",
    ):
        episode = _new_episode(registry, context, fixture, phase)
        if phase in ("confirm_pair", "abort_pair", "rollback_vs_confirm"):
            _start(registry, context, fixture, episode)
        workers = _race(registry, context, fixture, episode, phase)
        _check(registry, context, fixture, episode, {"phase": phase, "workers": workers})
        if phase == "abort_pair":
            with registry.cursor() as cursor:
                actor = api.Environment(cursor, fixture["users"][0], context)
                first = actor["mc.rov.revision"].browse(episode["revisions"][0])
                first.write(
                    {
                        "umbilical": "equipo",
                        "largo": 100,
                        "alimentacion": "Generador",
                        "tension_salida": 220,
                        "funcionamiento_continuo_duracion": 1.5,
                        "funcionamiento_continuo_resultado": "ok",
                    }
                )
                first.chequeo_ids.write({"resultado": "ok"})
                first.inspeccion_ids.write({"estado_sello": "intacto"})
                before = first._acceptance_attempts().read()
                cursor.commit()
            workers = _race(registry, context, fixture, episode, "restart_pair")
            with registry.cursor() as cursor:
                actor = api.Environment(cursor, fixture["users"][1], context)
                first = actor["mc.rov.revision"].browse(episode["revisions"][0])
                first.action_confirmar()
                assert first._acceptance_attempts()[:1].read() == before
                cursor.commit()
            _check(
                registry, context, fixture, episode, {"phase": "restart_pair", "workers": workers}
            )
    print("REPAIR_ACCEPTANCE_RACE_PROBE=PASSED")


shell_env = globals()["env"]
shell_env.cr.rollback()
run_probe(shell_env.registry, shell_env.cr.dbname)
