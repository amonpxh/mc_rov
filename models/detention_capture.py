"""Registra hechos F2 con permisos del origen; no pausa ni dirige la operación."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .detention_history import _CAPABILITY, _KEY
from .detention_kpi_metrics import CAUSES
from .production_kpi_event import lock_source


SOURCES = {"repair.order": "repair_id", "mrp.production": "production_id"}
OPEN = {
    "repair.order": {"confirmed", "under_repair"},
    "mrp.production": {"confirmed", "progress", "to_close"},
}


def _positive_id(value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValidationError(_("Seleccione un registro válido."))
    return value


class DetentionService(models.AbstractModel):
    """Autoriza cada orden antes de elevar únicamente el acceso al historial privado."""

    _name = "mc.rov.detention.service"
    _description = "Registro autorizado de detenciones ROV"

    def _source(self, model, identity, operation="read"):
        if not isinstance(model, str) or model not in SOURCES:
            raise ValidationError(_("Seleccione una orden de Reparación o Fabricación."))
        user = self.env.user
        if user.share or user._is_public() or not user.has_group("base.group_user"):
            raise AccessError(_("Se requiere una cuenta interna autorizada."))
        companies = self.env.companies
        source = self.env[model].browse(_positive_id(identity)).exists()
        if not source:
            raise AccessError(_("La orden no está disponible."))
        source.check_access(operation)
        if source.company_id not in companies:
            raise AccessError(_("La orden no pertenece a una empresa activa autorizada."))
        return source

    def _ledger(self):
        return self.env["mc.rov.detention.interval"].sudo().with_context(**{_KEY: _CAPABILITY})

    def _rows(self, source):
        rows = self._ledger().search([(SOURCES[source._name], "=", source.id)])
        if rows.filtered(lambda row: row.company_id != source.company_id):
            raise AccessError(_("La empresa del historial no coincide con la orden."))
        return rows

    def _protect_company(self, sources, values):
        if "company_id" not in values:
            return
        sources.check_access("write")
        for source in sources:
            if values["company_id"] != source.company_id.id:
                lock_source(source)
                if self._ledger().search_count([(SOURCES[source._name], "=", source.id)]):
                    raise UserError(
                        _("No cambie la empresa de una orden con historial de detenciones.")
                    )

    def _validate_start(self, source, cause, employee_id, explanation):
        if source.state not in OPEN[source._name]:
            raise UserError(_("Solo se registra detención en una orden confirmada y abierta."))
        if cause not in CAUSES:
            raise ValidationError(_("Seleccione una causa de detención válida."))
        if not isinstance(explanation, str):
            raise ValidationError(_("La explicación debe ser texto."))
        if cause == "other" and not explanation.strip():
            raise UserError(_("Explique la causa Otro."))
        product = source.product_id
        product.check_access("read")
        root = self.env["stock.lot"]._get_rov_root_category()
        if not root or not self.env["product.category"].search_count(
            [("id", "=", product.categ_id.id), ("id", "child_of", root.id)]
        ):
            raise UserError(_("La orden debe corresponder a un ROV."))
        employee = self.env["hr.employee.public"].browse(_positive_id(employee_id)).exists()
        if not employee:
            raise AccessError(_("El empleado responsable no está disponible."))
        employee.check_access("read")
        if employee.company_id != source.company_id:
            raise AccessError(_("El responsable debe pertenecer a la empresa de la orden."))
        return employee

    @api.model
    # El contrato RPC separa modelo/ID del origen, causa, empleado y explicación.
    # pylint: disable=too-many-arguments
    def start_detention(self, model, identity, cause, responsible_employee_id, explanation=""):
        source = self._source(model, identity, "write")
        lock_source(source)
        employee = self._validate_start(source, cause, responsible_employee_id, explanation)
        if self._rows(source).filtered(lambda row: not row.ended_at and row.cause == cause):
            raise UserError(_("Ya existe una detención abierta por esta causa."))
        row = self._ledger().create(
            {
                SOURCES[model]: source.id,
                "company_id": source.company_id.id,
                "cause": cause,
                "responsible_employee_id": employee.id,
                "actor_id": self.env.uid,
                "started_at": fields.Datetime.now(),
                "explanation": explanation.strip(),
            }
        )
        return row.id

    def _finish(self, rows, explanation, kind):
        pending = rows.filtered(lambda row: not row.ended_at)
        if pending:
            pending.write(
                {
                    "ended_at": fields.Datetime.now(),
                    "closed_by_id": self.env.uid,
                    "closing_explanation": explanation.strip(),
                    "end_kind": kind,
                }
            )

    @api.model
    def finish_detention(self, identity, explanation=""):
        if not isinstance(explanation, str):
            raise ValidationError(_("La explicación debe ser texto."))
        row = self._ledger().browse(_positive_id(identity)).exists()
        if not row:
            raise AccessError(_("La detención no está disponible."))
        model = "repair.order" if row.repair_id else "mrp.production"
        identity_source = row.repair_id.id if row.repair_id else row.production_id.id
        source = self._source(model, identity_source, "write")
        lock_source(source)
        row.invalidate_recordset()
        if row.company_id != source.company_id:
            raise AccessError(_("La empresa de la detención no coincide con la orden."))
        self._finish(row, explanation, "resumed")
        return row.id

    @api.model
    def get_intervals(self, model, identity):
        source = self._source(model, identity)
        return [
            {
                "id": row.id,
                "cause": row.cause,
                "started_at": fields.Datetime.to_string(row.started_at),
                "ended_at": (fields.Datetime.to_string(row.ended_at) if row.ended_at else False),
                "actor_id": row.actor_id.id,
                "closed_by_id": row.closed_by_id.id,
                "responsible_employee_id": row.responsible_employee_id.id,
                "explanation": row.explanation or "",
                "closing_explanation": row.closing_explanation or "",
                "end_kind": row.end_kind or False,
            }
            for row in self._rows(source)
        ]

    def _finish_closed_sources(self, sources):
        for source in sources:
            pending = self._rows(source).filtered(lambda row: not row.ended_at)
            if pending:
                self._source(source._name, source.id, "write")
                self._finish(pending, _("Fin por cierre de orden."), "source_closed")


class RepairDetentionCapture(models.Model):
    """El cierre real limita detenciones; no simula una reanudación del trabajo."""

    _inherit = "repair.order"

    def write(self, values):
        self.env["mc.rov.detention.service"]._protect_company(self, values)
        closing = values.get("state") in ("done", "cancel")
        if closing:
            lock_source(self)
        result = super().write(values)
        if closing:
            self.env["mc.rov.detention.service"]._finish_closed_sources(self)
        return result


class ManufacturingDetentionCapture(models.Model):
    """Cierra intervalos al terminar/cancelar sin alterar las operaciones nativas."""

    _inherit = "mrp.production"

    def write(self, values):
        self.env["mc.rov.detention.service"]._protect_company(self, values)
        closing = values.get("state") in ("done", "cancel")
        if closing:
            lock_source(self)
        result = super().write(values)
        if closing:
            self.env["mc.rov.detention.service"]._finish_closed_sources(self)
        return result

    def _action_cancel(self):
        # Odoo calcula el estado al cancelar movimientos; no siempre llama a
        # write(state). Serializar antes y reconciliar después del evento real.
        lock_source(self)
        result = super()._action_cancel()
        closed = self.filtered(lambda order: order.state in ("done", "cancel"))
        self.env["mc.rov.detention.service"]._finish_closed_sources(closed)
        return result


class StockMoveDetentionCapture(models.Model):
    """Observa cierres MRP calculados por stock, conservando movimientos nativos."""

    _inherit = "stock.move"

    def _mc_detention_sources(self):
        moves = self.exists()
        productions = moves.production_id | moves.raw_material_production_id
        identities = [row.id for row in productions if isinstance(row.id, int) and row.id > 0]
        if not identities:
            return productions.browse()
        # No exige permisos MRP por movimientos ajenos al seguimiento F2.
        rows = (
            self.env["mc.rov.detention.service"]
            ._ledger()
            .search(
                [
                    ("production_id", "in", identities),
                    ("ended_at", "=", False),
                ]
            )
        )
        return productions.browse(sorted(set(rows.production_id.ids)))

    def _action_done(self, *args, **kwargs):
        sources = self._mc_detention_sources()
        if sources:
            lock_source(sources)
        result = super()._action_done(*args, **kwargs)
        sources |= result._mc_detention_sources()
        closed = sources.filtered(lambda row: row.state in ("done", "cancel"))
        self.env["mc.rov.detention.service"]._finish_closed_sources(closed)
        return result

    def _action_cancel(self, *args, **kwargs):
        sources = self._mc_detention_sources()
        if sources:
            lock_source(sources)
        result = super()._action_cancel(*args, **kwargs)
        sources |= self._mc_detention_sources()
        closed = sources.filtered(lambda row: row.state in ("done", "cancel"))
        self.env["mc.rov.detention.service"]._finish_closed_sources(closed)
        return result
