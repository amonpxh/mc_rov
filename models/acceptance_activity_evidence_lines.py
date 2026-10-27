from odoo import api, models


def _line_revisions(lines, values):
    """Incluye ambos padres al mover una línea; NewId nunca identifica un ciclo real."""
    revisions = lines.revision_id
    for data in values:
        revision_id = data.get("revision_id", lines.env.context.get("default_revision_id"))
        if isinstance(revision_id, int) and revision_id > 0:
            revisions |= lines.env["mc.rov.revision"].browse(revision_id)
    return revisions.filtered(lambda record: isinstance(record.id, int) and record.id > 0)


def _line_event(lines, values, operation):
    """Bloquea el ciclo antes de mutar el resultado y reconcilia en la misma transacción."""
    with lines.env.cr.savepoint():
        revisions = _line_revisions(lines, values)
        service = lines.env["mc.rov.acceptance.activity.automation"]
        service._lock_acceptance_cycles(service._evidence_cycles(revisions))
        result = operation()
        service._reconcile(revisions._mc_acceptance_lots())
        return result


class AcceptanceChecklistLifecycle(models.Model):
    """El veredicto cambia al editar el checklist, sin escribir en la cabecera."""

    _inherit = "mc.rov.revision.chequeo"

    @api.model_create_multi
    def create(self, vals_list):
        parent = super()
        return _line_event(self, vals_list, lambda: parent.create(vals_list))

    def write(self, values):
        parent = super()
        return _line_event(self, [values], lambda: parent.write(values))

    def unlink(self):
        parent = super()
        return _line_event(self, [], parent.unlink)


class AcceptanceFindingLifecycle(models.Model):
    """Crear, corregir o retirar hallazgos también actualiza la elegibilidad de emisión."""

    _inherit = "mc.rov.revision.hallazgo"

    @api.model_create_multi
    def create(self, vals_list):
        parent = super()
        return _line_event(self, vals_list, lambda: parent.create(vals_list))

    def write(self, values):
        parent = super()
        return _line_event(self, [values], lambda: parent.write(values))

    def unlink(self):
        parent = super()
        return _line_event(self, [], parent.unlink)
