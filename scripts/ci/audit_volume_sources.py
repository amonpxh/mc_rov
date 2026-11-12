"""Audita métodos y campos para F4/F5/Q4 sin leer registros de negocio."""

import hashlib
import inspect
import json
import os
from pathlib import Path
import tempfile


TARGETS = {
    "repair.order": {
        "methods": (
            "action_repair_done",
            "action_repair_cancel",
            "action_repair_start",
            "write",
            "create",
        ),
        "fields": (
            "state",
            "company_id",
            "partner_id",
            "product_id",
            "lot_id",
            "move_id",
            "schedule_date",
            "date_done",
            "date_start",
            "date_end",
            "fecha_entrega_real",
            "tipo_intervencion_ids",
            "is_under_warranty",
            "under_warranty",
        ),
    },
    "mrp.production": {
        "methods": (
            "button_mark_done",
            "_post_inventory",
            "_action_done",
            "action_cancel",
            "write",
        ),
        "fields": (
            "state",
            "company_id",
            "product_id",
            "product_qty",
            "qty_produced",
            "product_uom_id",
            "production_group_id",
            "backorder_sequence",
            "lot_producing_ids",
            "move_finished_ids",
            "date_start",
            "date_finished",
            "sale_line_id",
            "origin",
        ),
    },
    "stock.move": {
        "methods": ("_action_done", "_action_cancel", "write"),
        "fields": (
            "state",
            "date",
            "company_id",
            "product_id",
            "quantity",
            "product_uom_qty",
            "product_uom",
            "production_id",
            "raw_material_production_id",
            "repair_id",
            "byproduct_id",
            "move_line_ids",
            "origin_returned_move_id",
            "location_id",
            "location_dest_id",
        ),
    },
    "stock.move.line": {
        "methods": ("_action_done", "write"),
        "fields": (
            "move_id",
            "date",
            "company_id",
            "product_id",
            "quantity",
            "product_uom_id",
            "lot_id",
            "state",
            "location_id",
            "location_dest_id",
        ),
    },
    "mc.rov.revision": {
        "methods": ("action_confirmar", "action_volver_a_borrador", "write", "create", "unlink"),
        "fields": (
            "estado",
            "fecha",
            "lot_id",
            "repair_id",
            "partner_id",
            "tipo",
            "company_id",
            "hallazgo_ids",
            "mc_acceptance_purpose",
            "mc_final_attempt_id",
            "mc_new_attempt_id",
        ),
    },
    "mc.rov.revision.hallazgo": {
        "methods": ("write", "create", "unlink"),
        "fields": (
            "revision_id",
            "hallazgo_id",
            "componente_id",
            "subtipo_id",
            "lot_id",
            "company_id",
            "severidad",
            "chequeo_origen_id",
            "fecha",
            "detected_at",
            "create_date",
        ),
    },
    "stock.lot": {
        "methods": (),
        "fields": (
            "product_id",
            "company_id",
            "production_ids",
            "mrp_production_ids",
            "repair_ids",
            "revision_ids",
            "mc_version_software",
            "mc_version_controlador",
            "mc_version_ardusub",
        ),
    },
    "product.template": {
        "methods": ("write",),
        "fields": (
            "categ_id",
            "tracking",
            "type",
            "is_storable",
            "company_id",
            "version",
            "eco_ids",
            "bom_ids",
        ),
    },
    "mrp.bom": {
        "methods": ("write", "copy"),
        "fields": (
            "version",
            "previous_bom_id",
            "active",
            "product_tmpl_id",
            "product_id",
            "company_id",
            "type",
            "code",
        ),
    },
    "mrp.eco": {
        "methods": ("action_apply", "action_new_revision", "write"),
        "fields": (
            "type",
            "state",
            "stage_id",
            "effectivity",
            "effectivity_date",
            "effective_date",
            "bom_id",
            "new_bom_id",
            "product_tmpl_id",
            "new_bom_revision",
            "will_update_version",
        ),
    },
    "mrp.unbuild": {
        "methods": ("action_unbuild",),
        "fields": ("state", "mo_id", "product_id", "lot_id", "company_id", "produce_line_ids"),
    },
}


def method_chain(model, name, checkout):
    """Conserva cada implementación, evitando confundir el primer override con toda la cadena."""
    result = []
    for cls in type(model).__mro__:
        function = cls.__dict__.get(name)
        if isinstance(function, (classmethod, staticmethod)):
            function = function.__func__
        if function is None:
            continue
        function = inspect.unwrap(function)
        module = getattr(function, "__module__", "")
        if not module.startswith("odoo.addons.") or module.startswith("odoo.addons.mail."):
            continue
        row = {"class": cls.__name__, "module": module}
        try:
            source = inspect.getsource(function)
            filename = inspect.getsourcefile(function)
        except (OSError, TypeError):
            row["source_available"] = False
        else:
            if module.startswith("odoo.addons.mc_rov."):
                if not filename or not Path(filename).resolve().is_relative_to(checkout):
                    raise RuntimeError("La fuente mc_rov no pertenece al checkout aislado")
            row.update(
                source_available=True,
                file=filename,
                sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
                source=source,
            )
        result.append(row)
    return result


def collect(environment, checkout):
    """Consulta definiciones del registry; no busca órdenes, resultados o clientes."""
    report = {
        "kind": "kpi-volume-source-audit-v1",
        "database": environment.cr.dbname,
        "individual_business_records_included": False,
        "business_actions_invoked": False,
        "secret_values_included": False,
        "models": {},
    }
    for name, target in TARGETS.items():
        model = environment[name]
        fields = {}
        for field_name in target["fields"]:
            field = model._fields.get(field_name)  # pylint: disable=protected-access
            if field is not None:
                fields[field_name] = {
                    "type": field.type,
                    "store": bool(field.store),
                    "readonly": bool(field.readonly),
                    "relation": getattr(field, "comodel_name", None),
                    "related": list(field.related) if field.related else None,
                }
        report["models"][name] = {
            "fields": fields,
            "missing_fields": sorted(set(target["fields"]) - set(fields)),
            "classification_candidates": sorted(
                field_name
                for field_name in model._fields  # pylint: disable=protected-access
                if any(part in field_name.lower() for part in ("protot", "incident", "detecc"))
            ),
            "methods": {
                method: method_chain(model, method, checkout) for method in target["methods"]
            },
        }
    for name, method, native_module in (
        ("repair.order", "action_repair_done", "odoo.addons.repair."),
        ("mrp.production", "button_mark_done", "odoo.addons.mrp."),
        ("stock.move", "_action_done", "odoo.addons.stock."),
    ):
        if not any(
            row["source_available"] and row["module"].startswith(native_module)
            for row in report["models"][name]["methods"][method]
        ):
            raise RuntimeError(f"No se obtuvo la implementación nativa de {name}.{method}")
    return report


def run_audit(environment):
    if environment is None or environment.cr.dbname != "odoo_test":
        raise RuntimeError("La auditoría solo admite odoo_test")
    checkout = Path(os.environ["KPI_SOURCE_REPO"]).resolve()
    environment.cr.rollback()
    try:
        environment.cr.execute("SET TRANSACTION READ ONLY")
        environment.cr.execute("SHOW transaction_read_only")
        if environment.cr.fetchone() != ("on",):
            raise RuntimeError("La transacción no confirmó READ ONLY")
        report = collect(environment, checkout)
    finally:
        environment.cr.rollback()
    report["readonly_rolled_back"] = True
    with tempfile.NamedTemporaryFile(
        prefix="mc-rov-tests.volume-source-",
        suffix=".log",
        mode="w",
        encoding="utf-8",
        dir=os.environ["RUNNER_TEMP"],
        delete=False,
    ) as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    print(f"CI_VOLUME_SOURCE_READONLY=PASSED MODELS={len(report['models'])}", flush=True)


if "env" in globals():
    run_audit(globals()["env"])
