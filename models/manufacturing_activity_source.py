from odoo import _, models
from odoo.exceptions import ValidationError


class ManufacturingActivitySource(models.AbstractModel):
    """Conserva la identidad de una fabricación seguida sin publicar su historial."""

    _inherit = "mc.rov.manufacturing.activity.automation"

    def _source_runs(self, productions, pending=False):
        productions = productions.filtered(
            lambda record: isinstance(record.id, int) and record.id > 0
        )
        runs = self.env["mc.rov.manufacturing.activity.run"].sudo()
        if not productions:
            return runs.browse()
        productions._mc_lock_manufacturing()
        domain = [("production_id", "in", productions.ids)]
        if pending:
            domain.append(("outcome", "=", "pending"))
        return runs.search(domain)

    def _check_source_changes(self, productions, values):
        relevant = {"product_id", "company_id"}.intersection(values)
        if not relevant:
            return
        runs = self._source_runs(productions, pending=True)
        followed = productions.browse(runs.production_id.ids)
        followed.invalidate_recordset(list(relevant))
        for production in followed:
            if any(production[name].id != values[name] for name in relevant):
                raise ValidationError(_("No puede cambiar el origen de un seguimiento pendiente."))

    def _check_source_deletion(self, productions):
        if self._source_runs(productions):
            raise ValidationError(
                _(
                    "Esta fabricación tiene historial de seguimiento y no se puede borrar. "
                    "Conserve la orden y cancele el trabajo cuando corresponda."
                )
            )


class ManufacturingProductionSource(models.Model):
    """El producto y la empresa del pendiente no se sustituyen durante su ejecución."""

    _inherit = "mrp.production"

    def write(self, values):
        self.env["mc.rov.manufacturing.activity.automation"]._check_source_changes(self, values)
        return super().write(values)

    def unlink(self):
        self.check_access("unlink")
        self.env["mc.rov.manufacturing.activity.automation"]._check_source_deletion(self)
        return super().unlink()
