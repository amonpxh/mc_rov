from odoo import _, api, models
from odoo.exceptions import AccessError, ValidationError


class InventoryActivitySource(models.AbstractModel):
    """Autoriza el documento antes de consultar su historial técnico privado."""

    _inherit = "mc.rov.inventory.activity.automation"

    def _runs(self, pickings, pending=False, access="write"):
        ids = sorted(
            {
                picking.id
                for picking in pickings
                if isinstance(picking.id, int)
                and not isinstance(picking.id, bool)
                and picking.id > 0
            }
        )
        runs = self.env["mc.rov.inventory.activity.run"].sudo()
        if not ids:
            return runs.browse()
        pickings = self.env["stock.picking"].with_user(self.env.uid).browse(ids).exists()
        pickings.check_access("read")
        pickings.check_access(access)
        if any(picking.company_id not in pickings.env.companies for picking in pickings):
            raise AccessError(_("La operación no pertenece a las empresas autorizadas."))
        self.env["mc.rov.inventory.activity.lifecycle"]._capture(pickings, access=access)
        domain = [("picking_id", "in", pickings.ids)]
        if pending:
            domain.append(("outcome", "=", "pending"))
        return runs.search(domain)

    def _check_source_changes(self, pickings, values):
        relevant = {
            "company_id",
            "picking_type_id",
            "location_id",
            "location_dest_id",
        }.intersection(values)
        if not relevant:
            return
        runs = self._runs(pickings, pending=True)
        followed = self.env["stock.picking"].browse(runs.picking_id.ids)
        followed.invalidate_recordset(list(relevant))
        for picking in followed:
            if any(picking[name].id != (values[name] or False) for name in relevant):
                raise ValidationError(
                    _(
                        "No puede cambiar empresa, tipo ni ubicaciones de una operación con "
                        "seguimiento pendiente. Conserve el documento original y cree otra operación."
                    )
                )

    def _check_source_deletion(self, pickings):
        if self._runs(pickings, access="read"):
            raise ValidationError(
                _(
                    "Esta operación tiene historial de seguimiento de inventario y no se puede borrar. "
                    "Conserve el documento y cancele el trabajo cuando corresponda."
                )
            )


class InventoryRunHistorySource(models.Model):
    """La auditoría privada permanece también frente a borrados administrativos."""

    _inherit = "mc.rov.inventory.activity.run"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_followed_history(self):
        if any(isinstance(row.id, int) and row.id > 0 for row in self):
            raise ValidationError(
                _("El historial de seguimiento de inventario no se puede borrar.")
            )


class InventoryCycleHistorySource(models.Model):
    """El compromiso original y la herencia del restante forman parte del historial."""

    _inherit = "mc.rov.inventory.activity.cycle"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_followed_history(self):
        if any(isinstance(row.id, int) and row.id > 0 for row in self):
            raise ValidationError(_("El historial del ciclo de inventario no se puede borrar."))
