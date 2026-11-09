"""Exercise joint RND/TRN capture with separate transactions on a neutralized clone."""

# stdout is the isolated runner evidence protocol, not application logging.
# pylint: disable=unknown-option-value,print-used,too-many-locals
import concurrent.futures
import copy
import json
from threading import Barrier, Event

from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import SUPERUSER_ID, Command, api
from odoo.exceptions import UserError


class ProbeRollback(Exception):
    """Discard the whole native confirmation after its history was captured."""


def _fixture(registry, context):
    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        assert not env["ir.cron"].search_count([("active", "=", True)])
        assert not env["ir.mail_server"].search_count([("active", "=", True)])
        assert env["ir.config_parameter"].get_param("mc_rov.entorno") == "STAGING"
        assert (
            env["ir.config_parameter"].get_param("web.base.url")
            == "http://127.0.0.1/isolated-concurrency"
        )
        control = env["mc.rov.automation.control"].search([("company_id", "=", env.company.id)])
        if control:
            control.enabled = False
        else:
            env["mc.rov.automation.control"].create(
                {"company_id": env.company.id, "enabled": False}
            )
        category = env["product.category"].create({"name": "QA joint acceptance"})
        env["ir.config_parameter"].set_param("mc_rov.rov_category_id", str(category.id))
        product = env["product.product"].create(
            {"name": "QA joint unit", "tracking": "serial", "categ_id": category.id}
        )
        employee = env["hr.employee"].create({"name": "QA joint technician"})
        users = []
        for index in range(2):
            user = env["res.users"].create(
                {
                    "name": f"QA joint actor {index}",
                    "login": f"qa_joint_race_{index}",
                    "company_id": env.company.id,
                    "company_ids": [Command.set(env.company.ids)],
                    "group_ids": [
                        Command.set(
                            [
                                env.ref(name).id
                                for name in (
                                    "base.group_user",
                                    "stock.group_stock_user",
                                    "mrp.group_mrp_user",
                                )
                            ]
                        )
                    ],
                }
            )
            users.append(user.id)
        fixture = {
            "company": env.company.id,
            "product": product.id,
            "employee": employee.id,
            "users": users,
        }
        cursor.commit()
        return fixture


def _revisions(env, fixture, lot):
    revisions = env["mc.rov.revision"].create(
        [
            {
                "lot_id": lot,
                "responsable_id": fixture["employee"],
                "tipo": kind,
                "mc_correction_required": "no",
                "mc_retest_required": "no",
            }
            for kind in ("rendimiento", "terreno")
        ]
    )
    revisions.write(
        {
            "umbilical": "equipo",
            "largo": 100,
            "alimentacion": "Generador",
            "tension_salida": 220,
            "funcionamiento_continuo_duracion": 1.5,
            "funcionamiento_continuo_resultado": "ok",
        }
    )
    for revision in revisions:
        assert revision.chequeo_ids
        revision.chequeo_ids.write({"resultado": "ok"})
        revision.inspeccion_ids.write({"estado_sello": "intacto"})
    return revisions


def _episode(registry, context, fixture, phase):
    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        product = env["product.product"].browse(fixture["product"])
        lot = env["stock.lot"].create(
            {
                "name": "QA-JOINT-" + phase,
                "product_id": product.id,
                "company_id": fixture["company"],
            }
        )
        production = env["mrp.production"].create(
            {
                "product_id": product.id,
                "product_qty": 1,
                "product_uom_id": product.uom_id.id,
                "company_id": fixture["company"],
            }
        )
        production.action_confirm()
        production.write({"lot_producing_ids": [Command.set(lot.ids)], "qty_producing": 1})
        production.with_context(skip_redirection=True).button_mark_done()
        assert production.state == "done"
        assert env["mc.rov.acceptance.activity.automation"]._produced_lots(production) == lot
        revisions = _revisions(env, fixture, lot.id)
        alternate = _revisions(env, fixture, lot.id) if phase == "competing_start" else revisions
        if phase in ("failure_vs_pass", "abort_vs_pass"):
            revisions[0].chequeo_ids[0].resultado = "no_ok"
        if phase == "abort_vs_pass":
            revisions[0].funcionamiento_continuo_duracion = 0
        episode = {
            "production": production.id,
            "lot": lot.id,
            "revisions": revisions.ids,
            "alternate": alternate.ids,
        }
        cursor.commit()
        return episode


def _start(env, episode, ids=None):
    env["mc.rov.new.acceptance"].start_attempt(
        episode["production"], episode["lot"], *(ids or episode["revisions"])
    )


def _action(env, episode, phase, index):
    if phase in ("start_pair", "competing_start", "restart_pair"):
        _start(
            env, episode, episode["alternate"] if phase == "competing_start" and index else None
        )
        return
    position = index if phase in ("phase_pair", "failure_vs_pass", "abort_vs_pass") else 0
    revision = env["mc.rov.revision"].browse(episode["revisions"][position])
    if phase == "abort_vs_pass" and index == 0:
        revision.action_abort_new_acceptance("QA fallo real durante protocolo incompleto")
    else:
        revision.action_confirmar()
    if phase == "rollback_vs_confirm" and index == 0:
        raise ProbeRollback()


def _race(registry, context, fixture, episode, phase):
    barrier = Barrier(2, timeout=20)

    def worker(index):
        first_pid, first_read = None, None
        for retry in range(1, 5):
            try:
                with registry.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout = '20s'")
                    cursor.execute("SET LOCAL statement_timeout = '45s'")
                    env = api.Environment(cursor, fixture["users"][index], context)
                    if retry == 1:
                        sources = env["mc.rov.revision"].browse(episode["revisions"])
                        first_read = sources.mapped("estado")
                        cursor.execute("SELECT pg_backend_pid()")
                        first_pid = cursor.fetchone()[0]
                        barrier.wait()
                    result = "committed"
                    try:
                        with cursor.savepoint():
                            _action(env, episode, phase, index)
                    except UserError as error:
                        assert error.__class__ is UserError
                        assert (
                            phase == "competing_start"
                            and "intento pendiente con otras pruebas" in str(error)
                        ), str(error)
                        result = "blocked"
                    cursor.commit()
                    return {
                        "pid": first_pid,
                        "actor": env.uid,
                        "read": first_read,
                        "attempts": retry,
                        "result": result,
                    }
            except ProbeRollback:
                return {
                    "pid": first_pid,
                    "actor": fixture["users"][index],
                    "read": first_read,
                    "attempts": retry,
                    "result": "rolled_back",
                }
            except (SerializationFailure, DeadlockDetected):
                if retry == 4:
                    raise
        raise AssertionError("Retries exhausted")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, index) for index in range(2)]
        return [future.result(timeout=150) for future in futures]


def _check(registry, context, fixture, episode, phase, workers, original=None):
    # Keep both worker receipts and the immutable pre-restart baseline together.
    # pylint: disable=too-many-arguments
    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        attempts = env["mc.rov.new.acceptance.attempt"].search(
            [("episode_id.lot_id", "=", episode["lot"])], order="ordinal"
        )
        assert len(attempts) == (2 if phase == "restart_pair" else 1)
        assert attempts.mapped("ordinal") == list(range(1, len(attempts) + 1))
        assert len(attempts.filtered(lambda row: row.state == "pending")) <= 1
        for row in attempts:
            assert row.episode_id.production_id.id == episode["production"]
            assert row.episode_id.company_id.id == fixture["company"]
            assert row.rnd_id.exists() and row.trn_id.exists() and row.episode_id.lot_id.exists()
            if row.state != "pending":
                assert row.closed_at and row.finished_by_id.id in fixture["users"]
            for key, result in row.requirements_snapshot.get("results", {}).items():
                source = row.rnd_id if key == "performance" else row.trn_id
                assert result["revision_id"] == source.id
                assert result["actor_id"] in fixture["users"] and result["captured_at"]
                assert result["evidence"]["product_id"] == fixture["product"]
                if phase in ("phase_pair", "failure_vs_pass", "abort_vs_pass"):
                    assert result["actor_id"] == fixture["users"][0 if key == "performance" else 1]
        last = attempts[-1]
        if phase in ("start_pair", "competing_start"):
            assert last.state == "pending" and not last.requirements_snapshot.get("results")
        elif phase in ("phase_pair", "restart_pair"):
            assert last.state == "confirmed" and last.first_pass_snapshot == "passed"
            assert set(last.requirements_snapshot["results"]) == {"performance", "field"}
            if original is not None:
                assert attempts[:1].read()[0] == original
        elif phase in ("failure_vs_pass", "abort_vs_pass"):
            assert last.state == "failed" and last.first_pass_snapshot == "failed"
            assert last.requirements_snapshot["results"]["performance"]["verdict"] == "rechazado"
        else:
            assert last.state == "pending" and set(last.requirements_snapshot["results"]) == {
                "performance"
            }
            if phase == "rollback_vs_confirm":
                assert (
                    last.requirements_snapshot["results"]["performance"]["actor_id"]
                    == fixture["users"][1]
                )
        if phase == "abort_vs_pass":
            assert last.rnd_id.estado == "borrador" and last.trn_id.estado == "confirmado"
        row = {
            "phase": phase,
            "workers": workers,
            "attempts": len(attempts),
            "states": attempts.mapped("state"),
            "first_pass": attempts.mapped("first_pass_snapshot"),
            "ordinals": attempts.mapped("ordinal"),
            "orphan_attempts": 0,
            "source_actor_verified": True,
            "first_failure_preserved": original is not None,
            "captured_phases": sorted(last.requirements_snapshot.get("results", {})),
        }
        print("NEW_ACCEPTANCE_FINAL_RACE_CASE=" + json.dumps(row))


def _flag_race(registry, context, fixture, episode):
    barrier = Barrier(2, timeout=20)
    confirmed = Event()

    def worker(index):
        first_pid, first_read, emission_before = None, None, None
        for retry in range(1, 5):
            try:
                with registry.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout = '20s'")
                    cursor.execute("SET LOCAL statement_timeout = '45s'")
                    actor = api.Environment(cursor, fixture["users"][index], context)
                    sources = actor["mc.rov.revision"].browse(episode["revisions"])
                    revision = sources[0]
                    if retry == 1:
                        first_read = sources.mapped("estado")
                        emission_before = revision.documento_emitido
                        assert emission_before is False
                        cursor.execute("SELECT pg_backend_pid()")
                        first_pid = cursor.fetchone()[0]
                        barrier.wait()
                    result = "committed"
                    try:
                        with cursor.savepoint():
                            if index == 0:
                                revision.action_confirmar()
                            else:
                                assert confirmed.wait(timeout=30), "Confirmation did not commit"
                                revision.write({"documento_emitido": False})
                    except UserError as error:
                        assert index == 1 and error.__class__ is UserError
                        assert "conserva su marca de emisión" in str(error), str(error)
                        result = "blocked"
                    cursor.commit()
                    if index == 0:
                        confirmed.set()
                    return {
                        "pid": first_pid,
                        "actor": actor.uid,
                        "read": first_read,
                        "emission_before": emission_before,
                        "attempts": retry,
                        "result": result,
                    }
            except (SerializationFailure, DeadlockDetected):
                if retry == 4:
                    raise
        raise AssertionError("Emission race retries exhausted")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, index) for index in range(2)]
        workers = [future.result(timeout=150) for future in futures]
    assert [row["result"] for row in workers] == ["committed", "blocked"]
    with registry.cursor() as cursor:
        check = api.Environment(cursor, SUPERUSER_ID, context)
        revision = check["mc.rov.revision"].browse(episode["revisions"][0])
        assert revision.estado == "confirmado" and revision.documento_emitido is True
        assert revision.write_uid.id == fixture["users"][0]
        assert not check["mc.rov.new.acceptance.attempt"].search_count(
            [("episode_id.lot_id", "=", episode["lot"])]
        )
        print(
            "NEW_ACCEPTANCE_FINAL_RACE_CASE="
            + json.dumps(
                {
                    "phase": "flag_clear_vs_confirm",
                    "workers": workers,
                    "attempts": 0,
                    "states": [],
                    "first_pass": [],
                    "ordinals": [],
                    "orphan_attempts": 0,
                    "source_actor_verified": True,
                    "first_failure_preserved": False,
                    "captured_phases": [],
                    "emission_flag_preserved": True,
                    "revision_state": "confirmado",
                }
            )
        )


def run_probe(registry, database):
    if not database.startswith("mc_rov_new_acceptance_final_ci_"):
        raise AssertionError("Joint acceptance requires its isolated database")
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
        "competing_start",
        "phase_pair",
        "duplicate_phase",
        "failure_vs_pass",
        "abort_vs_pass",
        "rollback_vs_confirm",
    ):
        episode = _episode(registry, context, fixture, phase)
        if phase not in ("start_pair", "competing_start"):
            with registry.cursor() as cursor:
                _start(api.Environment(cursor, fixture["users"][0], context), episode)
                cursor.commit()
        workers = _race(registry, context, fixture, episode, phase)
        _check(registry, context, fixture, episode, phase, workers)
        if phase == "failure_vs_pass":
            with registry.cursor() as cursor:
                env = api.Environment(cursor, SUPERUSER_ID, context)
                first = (
                    env["mc.rov.new.acceptance.attempt"]
                    .search([("episode_id.lot_id", "=", episode["lot"])])
                    .ensure_one()
                )
                original = copy.deepcopy(first.read()[0])
                episode["revisions"] = _revisions(env, fixture, episode["lot"]).ids
                cursor.commit()
            workers = _race(registry, context, fixture, episode, "restart_pair")
            with registry.cursor() as cursor:
                env = api.Environment(cursor, fixture["users"][0], context)
                env["mc.rov.revision"].browse(episode["revisions"]).action_confirmar()
                cursor.commit()
            _check(registry, context, fixture, episode, "restart_pair", workers, original)
    episode = _episode(registry, context, fixture, "flag_clear_vs_confirm")
    _flag_race(registry, context, fixture, episode)
    print("NEW_ACCEPTANCE_FINAL_RACE_PROBE=PASSED")


shell_env = globals()["env"]
shell_env.cr.rollback()
run_probe(shell_env.registry, shell_env.cr.dbname)
