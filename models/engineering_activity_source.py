from odoo import _, api, models
from odoo.exceptions import ValidationError


class EngineeringActivitySource(models.AbstractModel):
    """Mantiene el ECO histórico sin inmovilizar el contenido de su nueva revisión."""

    _inherit = "mc.rov.engineering.activity.automation"

    def _runs(self, ecos, pending=False, access="write"):
        ids = [
            eco.id
            for eco in ecos
            if isinstance(eco.id, int) and not isinstance(eco.id, bool) and eco.id > 0
        ]
        runs = self.env["mc.rov.engineering.activity.run"].sudo()
        if not ids:
            return runs.browse()
        ecos = self.env["mrp.eco"].browse(ids)
        self.env["mc.rov.engineering.activity.lifecycle"]._capture(ecos, access=access)
        domain = [("eco_id", "in", ids)]
        if pending:
            domain.append(("outcome", "=", "pending"))
        return runs.search(domain)

    def _check_source_changes(self, ecos, values):
        relevant = {"company_id", "product_tmpl_id", "bom_id", "type", "type_id"}.intersection(
            values
        )
        if not relevant:
            return
        runs = self._runs(ecos)
        followed = self.env["mrp.eco"].browse(runs.eco_id.ids)
        followed.invalidate_recordset(list(relevant))
        for eco in followed:
            changed = any(
                (eco[name] if name == "type" else eco[name].id) != (values[name] or False)
                for name in relevant
            )
            if changed:
                raise ValidationError(
                    _(
                        "No puede cambiar empresa, producto, BoM o tipo del origen de un seguimiento "
                        "de ingeniería. Conserve el cambio original y cree otro para una identidad distinta."
                    )
                )

    def _check_source_deletion(self, ecos):
        if self._runs(ecos, access="read"):
            raise ValidationError(
                _(
                    "Este cambio tiene historial de seguimiento de ingeniería y no se puede borrar. "
                    "Conserve el cambio original; puede archivarlo cuando corresponda."
                )
            )


class EngineeringRunHistorySource(models.Model):
    """El historial privado se conserva también frente al borrado administrativo."""

    _inherit = "mc.rov.engineering.activity.run"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_followed_history(self):
        if any(isinstance(row.id, int) and row.id > 0 for row in self):
            raise ValidationError(
                _("El historial de seguimiento de ingeniería no se puede borrar.")
            )


class EngineeringCycleHistorySource(models.Model):
    """El aniversario y la identidad del ECO permanecen como parte de su auditoría."""

    _inherit = "mc.rov.engineering.activity.cycle"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_followed_history(self):
        if any(isinstance(row.id, int) and row.id > 0 for row in self):
            raise ValidationError(_("El historial del ciclo de ingeniería no se puede borrar."))
