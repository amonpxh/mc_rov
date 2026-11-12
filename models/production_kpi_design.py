"""Identifica la configuración utilizada, sin aplicar la última versión al pasado."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


_SNAPSHOT = object()
_KEY = "mc_production_design_capability"


def design_snapshot(bom):
    """Una configuración necesita BoM; la versión actual aislada no acredita montaje."""
    if not bom:
        return {"revision_key": False, "revision_label": False, "bom_id": False}
    template = bom.product_tmpl_id
    return {
        "model_id": template.id,
        "model_version": template.version,
        "bom_id": bom.id,
        "bom_version": bom.version,
        "revision_key": f"bom:{bom.id}:v{bom.version}:model:{template.id}:v{template.version}",
        "revision_label": f"{template.name} · diseño {template.version} · {bom.code or 'BoM'} r{bom.version}",
    }


class ProductionDesignSnapshot(models.Model):
    """Sella diseño al confirmar y actualiza solo ante cambio explícito de configuración."""

    _inherit = "mrp.production"

    mc_design_snapshot = fields.Json(readonly=True, copy=False)

    def _capture_design_snapshot(self):
        for production in self:
            production.with_context(**{_KEY: _SNAPSHOT}).write(
                {
                    "mc_design_snapshot": design_snapshot(production.bom_id),
                }
            )

    @api.model_create_multi
    def create(self, vals_list):
        if any(values.get("mc_design_snapshot") for values in vals_list):
            raise UserError(_("El diseño se acredita desde la confirmación de Fabricación."))
        return super().create(vals_list)

    def write(self, values):
        if "mc_design_snapshot" in values and self.env.context.get(_KEY) is not _SNAPSHOT:
            raise UserError(_("El diseño acreditado no se modifica por escritura directa."))
        result = super().write(values)
        if {"bom_id", "product_id"}.intersection(values):
            self.filtered(
                lambda row: row.state not in ("draft", "done", "cancel")
            )._capture_design_snapshot()
        return result

    def action_confirm(self):
        candidates = self.filtered(lambda row: row.state == "draft")
        result = super().action_confirm()
        candidates.filtered(
            lambda row: row.state not in ("draft", "cancel")
        )._capture_design_snapshot()
        return result
