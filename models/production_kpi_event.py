"""Hechos privados para medir producción sin depender de recordatorios activos."""

# Los dos catálogos pylint-odoo del proyecto difieren en method-required-super.
# pylint: disable=unknown-option-value

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import SQL


_CAPTURE = object()
_KEY = "mc_production_event_capability"


def event_values(event):
    """Normalización interna; el llamador ya debe haber autorizado el origen."""
    return {
        **event.payload,
        "identity": event.identity,
        "kind": event.kind,
        "at": fields.Datetime.to_string(event.at) if event.at else False,
        "lot_id": event.lot_id.id,
    }


def lock_source(source, access="write"):
    """Serializa también instantáneas que aún no veían un primer evento."""
    source.check_access(access)
    for identity in sorted(source.ids):
        source.env.cr.execute(
            SQL(
                "UPDATE %s SET write_date=write_date WHERE id=%s",
                SQL.identifier(source._table),
                identity,
            )
        )
    source.invalidate_recordset()


def unit_design(source, lot, company):
    """No adivina configuración histórica desde la versión actual del producto."""
    source.check_access("read")
    lot.check_access("read")
    rows = (
        source.env["mc.rov.production.event"]
        .sudo()
        .search(
            [
                ("kind", "=", "manufactured"),
                ("lot_id", "=", lot.id),
                ("company_id", "=", company.id),
            ]
        )
    )
    designs = {row.payload.get("revision_key") for row in rows}
    if len(designs) == 1 and False not in designs and None not in designs:
        return {
            key: rows[0].payload.get(key) for key in ("revision_key", "revision_label", "bom_id")
        }
    return {"revision_key": False, "revision_label": False, "bom_id": False}


def append_event(source, lot, kind, identity, payload, **links):
    """Entrada Python privada; autoriza el origen antes de elevar la escritura."""
    at = links.pop("at", False)
    source.ensure_one()
    lot.ensure_one()
    source.check_access("read")
    lot.check_access("read")
    lot.product_id.check_access("read")
    company = (
        source.company_id
        if "company_id" in source._fields
        else (
            source.repair_id.company_id
            if source.repair_id
            else lot.company_id or source.env.company
        )
    )
    if (
        source.env.user.share
        or source.env.user._is_public()
        or company not in source.env.companies
    ):
        raise AccessError(_("El hecho requiere un origen interno de una empresa autorizada."))
    if lot.company_id and lot.company_id != company:
        raise AccessError(_("La serie no pertenece a la empresa del hecho."))
    ledger = source.env["mc.rov.production.event"].sudo()
    existing = ledger.search(
        [("kind", "=", kind), ("identity", "=", identity), ("company_id", "=", company.id)],
        limit=1,
    )
    if existing:
        return existing
    return ledger.with_context(**{_KEY: _CAPTURE}).create(
        {
            "kind": kind,
            "identity": identity,
            "company_id": company.id,
            "lot_id": lot.id,
            "product_id": lot.product_id.id,
            "at": at,
            "actor_id": source.env.uid,
            "payload": {"model_id": lot.product_id.product_tmpl_id.id, **payload},
            **links,
        }
    )


class ProductionKPIEvent(models.Model):
    """Conserva identidad, fecha y dimensiones del hecho; sin ACL de lectura general."""

    _name = "mc.rov.production.event"
    _description = "Evidencia de producción y hallazgos ROV"
    _check_company_auto = True
    _order = "at, id"

    kind = fields.Selection(
        [
            ("repair_done", "Cierre técnico"),
            ("manufactured", "Fabricación"),
            ("accepted", "Aceptación"),
            ("released", "Liberación"),
            ("outbound", "Salida al cliente"),
            ("reversed", "Reverso"),
            ("observation", "Observación"),
            ("unit_movement", "Movimiento de unidad"),
            ("observation_correction", "Corrección de observación"),
        ],
        required=True,
        index=True,
    )
    identity = fields.Char(required=True, index=True)
    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    lot_id = fields.Many2one("stock.lot", required=True, ondelete="restrict", check_company=True)
    product_id = fields.Many2one(
        "product.product", required=True, ondelete="restrict", check_company=True
    )
    repair_id = fields.Many2one("repair.order", ondelete="restrict", check_company=True)
    production_id = fields.Many2one("mrp.production", ondelete="restrict", check_company=True)
    revision_id = fields.Many2one("mc.rov.revision", ondelete="restrict")
    move_id = fields.Many2one("stock.move", ondelete="restrict", check_company=True)
    at = fields.Datetime(index=True)
    actor_id = fields.Many2one("res.users", required=True, ondelete="restrict")
    payload = fields.Json(required=True)
    _event_unique = models.Constraint(
        "UNIQUE(company_id, kind, identity)", "Este hecho ya tiene evidencia registrada."
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su or self.env.context.get(_KEY) is not _CAPTURE:
            raise UserError(_("La evidencia se crea desde el evento real de negocio."))
        return super().create(vals_list)

    def write(self, values):
        # pylint: disable=method-required-super
        raise UserError(_("La evidencia histórica no se modifica."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_history(self):
        raise UserError(_("La evidencia histórica no se elimina."))
