"""Siete carreras sobre copia efímera de odoo_test, nunca sobre una base servida."""

# El informe de stdout es un protocolo CI; los casos usan solo identidades QA propias.
# pylint: disable=unknown-option-value,print-used,too-many-locals

import concurrent.futures
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from threading import Barrier
from unittest.mock import patch
import uuid

from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import SUPERUSER_ID, Command, api, fields, sql_db
from odoo.modules.module import get_module_path, initialize_sys_path
from odoo.modules.registry import Registry
from odoo.tools import SQL, config
from odoo.tools.misc import exec_pg_environ, find_pg_tool

from customer_commitment_races import run_customer_commitment_races
from run_kpi_browser_tests import run_browser


class ProbeRollback(Exception):
    """Revierte el negocio completo después de haber creado su evidencia."""


def _complete(revision):
    revision.write(
        {
            "umbilical": "equipo",
            "largo": 100,
            "alimentacion": "Generador",
            "tension_salida": 220,
            "funcionamiento_continuo_duracion": 1.5,
            "funcionamiento_continuo_resultado": "ok",
            "mc_correction_required": "no",
            "mc_retest_required": "no",
        }
    )
    revision.chequeo_ids.write({"resultado": "ok"})
    revision.inspeccion_ids.write({"estado_sello": "intacto"})


def _base(registry):
    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, {})
        env["ir.cron"].search([]).write({"active": False})
        env["ir.mail_server"].search([]).write({"active": False})
        company = env["res.company"].create({"name": "QA Carreras KPI"})
        context = {
            "allowed_company_ids": company.ids,
            "tracking_disable": True,
            "mail_notify_force_send": False,
            "no_reset_password": True,
        }
        env = api.Environment(cursor, SUPERUSER_ID, context)
        env["mc.rov.automation.control"].create({"company_id": company.id, "enabled": False})
        warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
        if not warehouse:
            warehouse = env["stock.warehouse"].create(
                {"name": "QA Carreras", "code": "KPR", "company_id": company.id}
            )
        category = env["product.category"].create({"name": "QA Carreras ROV"})
        env["ir.config_parameter"].set_param("mc_rov.rov_category_id", str(category.id))
        product = env["product.product"].create(
            {
                "name": "QA Unidad carreras",
                "tracking": "serial",
                "categ_id": category.id,
                "company_id": company.id,
            }
        )
        bom = env["mrp.bom"].create(
            {"product_tmpl_id": product.product_tmpl_id.id, "company_id": company.id}
        )
        employee = env["hr.employee"].create(
            {"name": "QA Técnico carreras", "company_id": company.id}
        )
        groups = env["res.groups"].browse(
            [
                env.ref(name).id
                for name in (
                    "base.group_user",
                    "stock.group_stock_user",
                    "mrp.group_mrp_manager",
                    "mc_rov.group_work_assignment_team",
                )
            ]
        )
        users = (
            env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                [
                    {
                        "name": f"QA Actor KPI {number}",
                        "login": f"qa_kpi_race_{uuid.uuid4().hex}",
                        "company_id": company.id,
                        "company_ids": [Command.set(company.ids)],
                        "group_ids": [Command.set(groups.ids)],
                    }
                    for number in range(2)
                ]
            )
        )
        fixture = {
            "company": company.id,
            "product": product.id,
            "bom": bom.id,
            "warehouse": warehouse.id,
            "employee": employee.id,
            "users": users.ids,
        }
        cursor.commit()
    return fixture, context


def _case(registry, context, fixture, phase):
    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        product = env["product.product"].browse(fixture["product"])
        lot = env["stock.lot"].create(
            {"name": "QA-" + phase, "product_id": product.id, "company_id": fixture["company"]}
        )
        case = {"phase": phase, "lot": lot.id}
        if phase.startswith("repair"):
            record = env["repair.order"].create(
                {
                    "product_id": product.id,
                    "product_qty": 1,
                    "lot_id": lot.id,
                    "company_id": fixture["company"],
                    "tipo_intervencion_ids": [
                        Command.set(env.ref("mc_rov.tipo_reparacion_correctiva").ids)
                    ],
                }
            )
            case.update(model="repair.order", source=record.id, state="state", kind="repair_done")
        elif phase in ("manufacture_pair", "release_pair", "joint_phases"):
            record = env["mrp.production"].create(
                {
                    "product_id": product.id,
                    "product_qty": 1,
                    "product_uom_id": product.uom_id.id,
                    "bom_id": fixture["bom"],
                    "picking_type_id": env["stock.warehouse"]
                    .browse(fixture["warehouse"])
                    .manu_type_id.id,
                    "company_id": fixture["company"],
                }
            )
            record.action_confirm()
            record.write({"lot_producing_ids": [Command.set(lot.ids)], "qty_producing": 1})
            case.update(
                model="mrp.production", source=record.id, state="state", kind="manufactured"
            )
            if phase in ("release_pair", "joint_phases"):
                record.with_context(skip_redirection=True).button_mark_done()
                revisions = env["mc.rov.revision"].create(
                    [
                        {"lot_id": lot.id, "tipo": kind, "responsable_id": fixture["employee"]}
                        for kind in ("rendimiento", "terreno")
                    ]
                )
                for revision in revisions:
                    _complete(revision)
                env["mc.rov.new.acceptance"].start_attempt(
                    record.id, lot.id, revisions[0].id, revisions[1].id
                )
                if phase == "joint_phases":
                    case.update(
                        model="mc.rov.revision",
                        source=revisions[0].id,
                        sources=revisions.ids,
                        state="estado",
                        kind="accepted",
                    )
                    cursor.commit()
                    return case
                revisions.action_confirmar()
                fen = env["mc.rov.ficha.equipo.nuevo"].create(
                    {"lot_id": lot.id, "rnd_id": revisions[0].id, "trn_id": revisions[1].id}
                )
                # La carrera comprueba la decisión de liberación, no el motor PDF.
                # El render real se comprueba por los HttpCase poblados del mismo CI.
                with patch.object(
                    type(env["ir.actions.report"]),
                    "_render_qweb_pdf",
                    return_value=(b"%PDF-1.4\nQA race\n%%EOF", "pdf"),
                ):
                    fen.action_emitir()
                case.update(kind="released", fen=fen.id)
        else:
            record = env["mc.rov.revision"].create(
                {
                    "lot_id": lot.id,
                    "tipo": "reparacion",
                    "motivo": "otro",
                    "responsable_id": fixture["employee"],
                }
            )
            _complete(record)
            finding = env["mc.rov.revision.hallazgo"].create(
                {
                    "revision_id": record.id,
                    "componente_id": env.ref("mc_rov.comp_motor").id,
                    "hallazgo_id": env.ref("mc_rov.hallazgo_corrosion").id,
                    "severidad": "informativo",
                    "mc_detected_at": fields.Datetime.now(),
                }
            )
            case.update(
                model="mc.rov.revision", source=record.id, state="estado", kind="observation"
            )
            if phase == "correction_pair":
                record.action_confirmar()
                record.action_volver_a_borrador()
                finding.severidad = "atencion"
                record.mc_findings_correction_reason = "Clasificación QA corregida con evidencia"
                case["kind"] = "observation_correction"
        cursor.commit()
    return case


def _action(env, case):
    record = env[case["model"]].browse(case["source"])
    if case["phase"].startswith("repair"):
        record.action_repair_done()
    elif case["phase"] == "manufacture_pair":
        if record.state != "done":
            record.with_context(skip_redirection=True).button_mark_done()
    elif case["phase"] == "release_pair":
        record._release_rov_unit(
            env["stock.lot"].browse(case["lot"]),
            env["mc.rov.ficha.equipo.nuevo"].browse(case["fen"]),
            True,
        )
    else:
        record.action_confirmar()


def _race(registry, context, fixture, case):
    barrier = Barrier(2, timeout=20)

    def worker(index):
        first_pid, first_state = None, None
        own_case = {**case, "source": case.get("sources", [case["source"]] * 2)[index]}
        for attempt in range(1, 5):
            try:
                with registry.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout='20s'")
                    cursor.execute("SET LOCAL statement_timeout='45s'")
                    env = api.Environment(cursor, fixture["users"][index], context)
                    if attempt == 1:
                        first_state = env[own_case["model"]].browse(own_case["source"])[
                            own_case["state"]
                        ]
                        cursor.execute("SELECT pg_backend_pid()")
                        first_pid = cursor.fetchone()[0]
                        barrier.wait()
                    _action(env, own_case)
                    if case["phase"] == "repair_rollback" and index == 0:
                        raise ProbeRollback()
                    cursor.commit()
                    return {
                        "pid": first_pid,
                        "read": first_state,
                        "attempts": attempt,
                        "result": "committed",
                    }
            except ProbeRollback:
                return {
                    "pid": first_pid,
                    "read": first_state,
                    "attempts": attempt,
                    "result": "rolled_back",
                }
            except (SerializationFailure, DeadlockDetected):
                if attempt == 4:
                    raise
        raise AssertionError("Reintentos agotados")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        workers = [pool.submit(worker, number) for number in range(2)]
        outcomes = [future.result(timeout=180) for future in workers]
    assert len({row["pid"] for row in outcomes}) == 2
    assert outcomes[0]["read"] == outcomes[1]["read"]
    with registry.cursor() as cursor:
        env = api.Environment(cursor, SUPERUSER_ID, context)
        evidence = env["mc.rov.production.event"].search(
            [("lot_id", "=", case["lot"]), ("kind", "=", case["kind"])]
        )
        assert len(evidence) == 1, (case["phase"], len(evidence))
        assert evidence.actor_id.id in fixture["users"]
        if case["phase"] == "repair_rollback":
            assert evidence.actor_id.id == fixture["users"][1]
        if case["model"] == "repair.order":
            assert env["stock.move"].search_count([("repair_id", "=", case["source"])]) == 1
        assert evidence.lot_id.product_id == evidence.product_id
    return {"phase": case["phase"], "workers": outcomes, "events": 1, "actor_verified": True}


def _admin(statement, name):
    if not re.fullmatch(r"mc_rov_kpi_ci_[a-f0-9]{20}", name):
        raise RuntimeError("Nombre de copia CI no permitido")
    with sql_db.db_connect("postgres").cursor() as cursor:
        cursor._cnx.autocommit = True  # pylint: disable=protected-access
        cursor.execute(SQL(statement, SQL.identifier(name)))


def _source_fingerprint():
    """Agregados de solo lectura; cerrar también el pool permite copiar la plantilla."""
    try:
        with sql_db.db_connect("odoo_test").cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            result = []
            for table in (
                "repair_order",
                "mrp_production",
                "stock_move",
                "stock_quant",
                "mc_rov_revision",
                "mc_rov_production_event",
                "mc_rov_customer_commitment",
                "mc_rov_customer_commitment_change",
                "mc_rov_customer_dispatch",
            ):
                cursor.execute(
                    SQL("SELECT count(*), max(write_date) FROM %s", SQL.identifier(table))
                )
                result.append(cursor.fetchone())
            cursor.rollback()
        return result
    finally:
        sql_db.close_db("odoo_test")


def _restore_source(database):
    """No exige ser dueño de odoo_test ni habilita funciones de administración web."""
    with tempfile.TemporaryDirectory(
        prefix="mc-rov-kpi-dump-", dir=os.environ["RUNNER_TEMP"]
    ) as work:
        backup = Path(work) / "source.dump"
        subprocess.run(
            [
                find_pg_tool("pg_dump"),
                "--no-owner",
                "--format=custom",
                "--file",
                str(backup),
                "odoo_test",
            ],
            env=exec_pg_environ(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )
        subprocess.run(
            [
                find_pg_tool("pg_restore"),
                "--no-owner",
                "--no-privileges",
                "--exit-on-error",
                "--dbname=" + database,
                str(backup),
            ],
            env=exec_pg_environ(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )


def main():
    repo = Path(sys.argv[1]).resolve()
    config.parse_config(
        [
            "-c",
            sys.argv[2],
            "--addons-path",
            sys.argv[3],
            "--no-http",
            "--max-cron-threads",
            "0",
            "--workers",
            "0",
        ]
    )
    initialize_sys_path()
    if repo.name != "mc_rov" or Path(get_module_path("mc_rov")).resolve() != repo:
        raise RuntimeError("Las fuentes no corresponden al checkout CI")
    if str(repo).startswith(("/opt/odoo/custom-addons", "/opt/odoo/staging-addons")):
        raise RuntimeError("No se ejecutan carreras desde un checkout servido")
    database = "mc_rov_kpi_ci_" + uuid.uuid4().hex[:20]
    created, passed = False, False
    report = {
        "source": "odoo_test",
        "cases": [],
        "f3_cases": [],
        "f3_browser": False,
        "pdf_renderer_test_double": True,
        "source_unchanged": None,
    }
    baseline = _source_fingerprint()
    try:
        _admin("CREATE DATABASE %s TEMPLATE template0", database)
        created = True
        _restore_source(database)
        registry = Registry.new(database)
        fixture, context = _base(registry)
        for phase in (
            "repair_pair",
            "repair_rollback",
            "manufacture_pair",
            "revision_pair",
            "release_pair",
            "correction_pair",
            "joint_phases",
        ):
            case = _case(registry, context, fixture, phase)
            report["cases"].append(_race(registry, context, fixture, case))
        assert len(report["cases"]) == 7
        run_customer_commitment_races(registry, context, fixture, report["f3_cases"])
        assert len(report["f3_cases"]) == 6
        result, rc = run_browser(
            repo,
            sys.argv[2],
            sys.argv[3],
            database,
            "customer_commitment_browser",
        )
        started = re.findall(r"Starting TestCustomerCommitmentBrowser\.(test_\w+)", result)
        report["f3_browser"] = bool(
            rc == 0
            and started == ["test_operational_repair_pickup_and_dashboard"]
            and re.search(r"0 failed, 0 error\(s\) of 1 tests", result)
            and len(re.findall(r"\.browser: test successful\s*$", result, re.M)) == 3
        )
        assert report["f3_browser"], "El navegador F3 no confirmó el recorrido completo"
        report["source_unchanged"] = _source_fingerprint() == baseline
        assert report["source_unchanged"], "Cambió la referencia de odoo_test"
        passed = True
    finally:
        if created:
            Registry.delete(database)
            sql_db.close_db(database)
            if passed:
                _admin("DROP DATABASE %s", database)
                filestore = Path(config.filestore(database)).resolve()
                root = Path(config.filestore("odoo_test")).resolve().parent
                if filestore.parent != root or filestore.name != database:
                    raise RuntimeError(
                        "La ruta del filestore temporal no está dentro del destino CI"
                    )
                if filestore.exists():
                    shutil.rmtree(filestore)
            else:
                _admin("ALTER DATABASE %s ALLOW_CONNECTIONS false", database)
                report["failed_copy_blocked"] = database
        report.update(passed=passed, isolated=True)
        with tempfile.NamedTemporaryFile(
            prefix="mc-rov-tests.production-races-",
            suffix=".log",
            mode="w",
            encoding="utf-8",
            dir=os.environ["RUNNER_TEMP"],
            delete=False,
        ) as output:
            json.dump(report, output, ensure_ascii=False, indent=2)
    print("CI_PRODUCTION_RACES=PASSED CASES=7 CONNECTIONS=2", flush=True)
    print("CI_F3_QA=PASSED RACES=6 CONNECTIONS=2 BROWSER_ROUTES=3", flush=True)


if __name__ == "__main__":
    main()
