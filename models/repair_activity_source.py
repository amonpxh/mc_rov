from odoo import _, models
from odoo.exceptions import ValidationError
from odoo.tools import SQL


class RepairActivitySource(models.AbstractModel):
    """Protege la identidad de la etapa sin dar acceso público al historial."""

    _inherit = "mc.rov.repair.activity.automation"

    def _source_runs(self, records, relation, pending=False):
        records.check_access("write")
        orders = records if relation == "repair_id" else records.mapped("repair_id")
        if orders:
            # Serializar con generación/cierre antes de consultar el historial privado.
            self.env.cr.execute(
                SQL(
                    "SELECT id FROM %s WHERE id IN %s ORDER BY id FOR UPDATE",
                    SQL.identifier(orders._table),
                    tuple(sorted(orders.ids)),
                )
            )
        domain = [(relation, "in", records.ids)]
        if pending:
            domain.append(("outcome", "=", "pending"))
        return self.env["mc.rov.repair.activity.run"].sudo().search(domain)

    def _check_source_changes(self, records, values, relation, protected):
        relevant = protected.intersection(values)
        records = records.filtered(lambda record: isinstance(record.id, int) and record.id > 0)
        if not relevant or not records:
            return
        runs = self._source_runs(records, relation, pending=True)
        followed = records.browse(runs.mapped(relation).ids)
        followed.invalidate_recordset(list(relevant))
        for record in followed:
            for name in relevant:
                field = record._fields[name]
                current = record[name].id if field.type == "many2one" else record[name]
                if current != values[name]:
                    raise ValidationError(
                        _("No puede cambiar el origen de un seguimiento pendiente.")
                    )

    def _check_source_deletion(self, records, relation):
        if records and self._source_runs(records, relation):
            raise ValidationError(
                _(
                    "Este registro tiene historial de seguimiento y no se puede borrar. "
                    "Conserve el registro y cancele el trabajo cuando corresponda."
                )
            )


class RepairOrderActivitySource(models.Model):
    """Una orden seguida conserva el equipo y la empresa de su etapa pendiente."""

    _inherit = "repair.order"

    def write(self, vals):
        self.env["mc.rov.repair.activity.automation"]._check_source_changes(
            self, vals, "repair_id", {"lot_id", "product_id", "company_id"}
        )
        return super().write(vals)

    def unlink(self):
        self.check_access("unlink")
        self.env["mc.rov.repair.activity.automation"]._check_source_deletion(self, "repair_id")
        return super().unlink()


class RepairRevisionActivitySource(models.Model):
    """La REV exacta seguida no se reasigna a otro equipo, orden o tipo."""

    _inherit = "mc.rov.revision"

    def write(self, vals):
        self.env["mc.rov.repair.activity.automation"]._check_source_changes(
            self, vals, "revision_id", {"repair_id", "lot_id", "company_id", "tipo"}
        )
        return super().write(vals)

    def unlink(self):
        self.check_access("unlink")
        self.env["mc.rov.repair.activity.automation"]._check_source_deletion(self, "revision_id")
        return super().unlink()
