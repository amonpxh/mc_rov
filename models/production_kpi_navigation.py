"""Abre documentos públicos autorizados a partir de los mismos filtros del agregado."""

from odoo import _, api, models
from odoo.exceptions import ValidationError

from .production_kpi_metrics import local_day, period_bounds


SOURCES = {
    "repair_done": ("repair.order", "repair_id"),
    "manufactured": ("mrp.production", "production_id"),
    "accepted": ("mrp.production", "production_id"),
    "released": ("mrp.production", "production_id"),
    "outbound": ("stock.move", "move_id"),
    "observation": ("mc.rov.revision", "revision_id"),
}


class ProductionKPINavigation(models.AbstractModel):
    """El tablero no expone IDs del ledger privado ni inventa destinos por contexto."""

    _inherit = "mc.rov.production.kpi"

    @api.model
    def action_sources(self, kind, **filters):
        if not isinstance(kind, str) or kind not in SOURCES:
            raise ValidationError(_("El origen del indicador no es válido."))
        # Reutiliza la validación completa antes de preparar un dominio de origen.
        self.get_summary(**filters)
        sources = self._sources(filters.get("model_id", False))
        events = self._events(sources)
        revision = self._revision_options(sources[1], events, filters.get("revision", "latest"))[0]
        rows = self._dimension_filter(
            self._normalized(events),
            filters.get("customer_id", False),
            filters.get("severity", "all"),
            filters.get("intervention", "all"),
        )
        bounds = period_bounds(filters.get("date_from", False), filters.get("date_to", False))
        identities = set()
        for row in rows:
            day = local_day(row.get("at"))
            if row["kind"] != kind or day is None:
                continue
            if (bounds[0] and day < bounds[0]) or (bounds[1] and day > bounds[1]):
                continue
            if revision == "all" or row.get("revision_key") in revision:
                identities.add(row["identity"])
        model, field_name = SOURCES[kind]
        records = self.env[model].browse(
            events.filtered(lambda event: event.kind == kind and event.identity in identities)
            .mapped(field_name)
            .ids
        )
        records.check_access("read")
        return {
            "type": "ir.actions.act_window",
            "name": _("Documentos de origen del indicador"),
            "res_model": model,
            "view_mode": "list,form",
            "views": [(False, "list"), (False, "form")],
            "domain": [("id", "in", records.ids)],
            "context": {"active_test": False, "create": False},
        }


class DashboardProductionNavigation(models.AbstractModel):
    """La navegación vuelve a comprobar permisos y empresa al pulsar el indicador."""

    _inherit = "mc.rov.kpi.dashboard"

    @api.model
    def action_production_sources(self, kind, **filters):
        self._check_caller()
        return self.env["mc.rov.production.kpi"].action_sources(kind, **filters)
