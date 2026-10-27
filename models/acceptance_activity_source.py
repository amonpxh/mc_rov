from odoo import _, models
from odoo.exceptions import ValidationError


class AcceptanceEvidenceSource(models.AbstractModel):
    """Conserva la identidad de las pruebas actuales y reemplazadas del ciclo."""

    _inherit = "mc.rov.acceptance.activity.automation"

    def _evidence_cycles(self, revisions):
        ids = [record.id for record in revisions if isinstance(record.id, int) and record.id > 0]
        cycles = self.env["mc.rov.acceptance.activity.cycle"].sudo()
        if not ids:
            return cycles.browse()
        current = cycles.search(["|", ("rnd_id", "in", ids), ("trn_id", "in", ids)])
        history = (
            self.env["mc.rov.acceptance.evidence.history"]
            .sudo()
            .search(["|", ("revision_id", "in", ids), ("previous_revision_id", "in", ids)])
        )
        return current | history.cycle_id

    def _check_evidence_source_changes(self, revisions, values):
        relevant = {"lot_id", "tipo", "repair_id"}.intersection(values)
        if not relevant:
            return
        revisions = revisions.filtered(lambda record: isinstance(record.id, int) and record.id > 0)
        cycles = self._evidence_cycles(revisions)
        if not cycles:
            return
        self._lock_acceptance_cycles(cycles)
        for revision in revisions:
            if not self._evidence_cycles(revision):
                continue
            revision.check_access("write")
            revision.invalidate_recordset(list(relevant))
            for name in relevant:
                current = (
                    revision[name].id
                    if revision._fields[name].type == "many2one"
                    else revision[name]
                )
                if current != values[name]:
                    raise ValidationError(
                        _(
                            "La evidencia de aceptación conserva su equipo, tipo y orden de origen. "
                            "Seleccione otra prueba con motivo si necesita reemplazarla."
                        )
                    )

    def _check_evidence_deletion(self, revisions):
        cycles = self._evidence_cycles(revisions)
        if cycles:
            self._lock_acceptance_cycles(cycles)
            raise ValidationError(
                _(
                    "Esta prueba tiene historial de aceptación y no se puede borrar. "
                    "Conserve la evidencia y seleccione otra prueba con motivo si corresponde."
                )
            )


class AcceptanceRevisionSource(models.Model):
    """Cambiar la identidad o borrar la prueba no puede reescribir el historial."""

    _inherit = "mc.rov.revision"

    def write(self, values):
        self.env["mc.rov.acceptance.activity.automation"]._check_evidence_source_changes(
            self, values
        )
        return super().write(values)

    def unlink(self):
        self.check_access("unlink")
        self.env["mc.rov.acceptance.activity.automation"]._check_evidence_deletion(self)
        return super().unlink()


class AcceptanceEvidenceHistorySource(models.Model):
    """La auditoría es privada y se conserva también para administradores."""

    _inherit = "mc.rov.acceptance.evidence.history"

    def unlink(self):
        self.check_access("unlink")
        if any(isinstance(record.id, int) and record.id > 0 for record in self):
            raise ValidationError(
                _("El historial de aceptación se conserva y no se puede borrar.")
            )
        return super().unlink()
