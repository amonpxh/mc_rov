from odoo import _, Command, models
from odoo.exceptions import ValidationError


class QualityActivitySource(models.AbstractModel):
    """El origen de una alerta seguida no se traslada al cambiar sus referencias."""

    _inherit = "mc.rov.quality.activity.automation"

    def _source_runs(self, alerts, pending=False, access="write"):
        alerts = alerts.filtered(lambda record: isinstance(record.id, int) and record.id > 0)
        runs = self.env["mc.rov.quality.activity.run"].sudo()
        if not alerts:
            return runs.browse()
        # Serializar también un origen aún sin seguimiento frente a un inicio concurrente.
        self.env["mc.rov.quality.activity.lifecycle"]._capture(alerts, access=access)
        domain = [("alert_id", "in", alerts.ids)]
        if pending:
            domain.append(("outcome", "=", "pending"))
        return runs.search(domain)

    def _remaining_serials(self, current, commands):
        """Evaluar solo enlaces; no crear, editar ni borrar series para validar el cambio."""
        if commands is False or commands is None:
            return set()
        if hasattr(commands, "ids"):
            return set(commands.ids)
        if isinstance(commands, tuple):
            return set(commands)
        if not commands:
            return set(current)
        if all(isinstance(command, int) for command in commands):
            return set(commands)
        result = set(current)
        for command in commands:
            operation = command[0]
            if operation in (Command.DELETE, Command.UNLINK):
                result.discard(command[1])
            elif operation == Command.LINK:
                result.add(command[1])
            elif operation == Command.CLEAR:
                result.clear()
            elif operation == Command.SET:
                result = set(command[2])
        return result

    def _check_source_changes(self, alerts, values):
        relevant = {"product_id", "product_tmpl_id", "company_id", "lot_ids"}.intersection(values)
        if not relevant:
            return
        runs = self._source_runs(alerts, pending=True)
        followed = alerts.browse(runs.alert_id.ids)
        followed.invalidate_recordset(list(relevant))
        for alert in followed:
            changed = any(alert[name].id != values[name] for name in relevant if name != "lot_ids")
            if "lot_ids" in relevant:
                current = set(alert.lot_ids.ids)
                changed = changed or not current <= self._remaining_serials(
                    current, values["lot_ids"]
                )
            if changed:
                raise ValidationError(
                    _(
                        "No puede cambiar el producto, modelo o empresa ni retirar series "
                        "del origen de un seguimiento pendiente. Conserve la alerta original."
                    )
                )

    def _check_source_deletion(self, alerts):
        if self._source_runs(alerts, access="read"):
            raise ValidationError(
                _(
                    "Esta alerta tiene historial de seguimiento y no se puede borrar. "
                    "Conserve la alerta y resuélvala cuando corresponda."
                )
            )


class QualityAlertSource(models.Model):
    """Protege referencias seguidas y explica la conservación antes del error de SQL."""

    _inherit = "quality.alert"

    def write(self, values):
        with self.env.cr.savepoint():
            self.env["mc.rov.quality.activity.automation"]._check_source_changes(self, values)
            return super().write(values)

    def unlink(self):
        self.check_access("unlink")
        self.env["mc.rov.quality.activity.automation"]._check_source_deletion(self)
        return super().unlink()


class QualityRunHistorySource(models.Model):
    """La auditoría privada se conserva también para quienes administran el sistema."""

    _inherit = "mc.rov.quality.activity.run"

    def unlink(self):
        self.check_access("unlink")
        if any(isinstance(record.id, int) and record.id > 0 for record in self):
            raise ValidationError(_("El historial de seguimiento de Calidad no se puede borrar."))
        return super().unlink()
