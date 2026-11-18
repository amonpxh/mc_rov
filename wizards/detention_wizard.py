"""Registro explícito de hechos F2 desde una única orden."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from ..models.detention_history import CAUSE_LABELS


class DetentionWizard(models.TransientModel):
    """Solicita causa, responsable o intervalo según la decisión del operador."""

    _name = "mc.rov.detention.wizard"
    _description = "Registrar inicio o reanudación de trabajo ROV"

    repair_id = fields.Many2one("repair.order", readonly=True)
    production_id = fields.Many2one("mrp.production", readonly=True)
    company_id = fields.Many2one("res.company", compute="_compute_company")
    decision = fields.Selection([("start", "Inicio"), ("finish", "Reanudación")], required=True)
    cause = fields.Selection(list(CAUSE_LABELS.items()), string="Causa")
    responsible_employee_id = fields.Many2one(
        "hr.employee.public", string="Responsable de destrabar"
    )
    explanation = fields.Text(string="Explicación")
    interval_key = fields.Char()
    option_ids = fields.One2many("mc.rov.detention.wizard.option", "wizard_id")
    option_id = fields.Many2one("mc.rov.detention.wizard.option", string="Detención")

    @api.depends("repair_id.company_id", "production_id.company_id")
    def _compute_company(self):
        for wizard in self:
            wizard.company_id = wizard.repair_id.company_id or wizard.production_id.company_id

    def action_apply(self):
        self.ensure_one()
        self.check_access("write")
        if bool(self.repair_id) == bool(self.production_id):
            raise ValidationError(_("Seleccione una única orden."))
        order = self.repair_id or self.production_id
        service = self.env["mc.rov.detention.service"]
        source = service._source(order._name, order.id, "write")
        if self.decision == "start":
            service.start_detention(
                source._name,
                source.id,
                self.cause,
                self.responsible_employee_id.id,
                self.explanation or "",
            )
        else:
            if self.option_id and self.option_id.wizard_id != self:
                raise AccessError(_("La detención no pertenece a este asistente."))
            key = self.option_id.interval_key if self.option_id else self.interval_key
            if not key or not key.isascii() or not key.isdecimal() or len(key) > 20:
                raise ValidationError(_("Seleccione una detención."))
            identity = int(key)
            if identity not in service._rows(source).ids:
                raise AccessError(_("La detención no pertenece a esta orden."))
            service.finish_detention(identity, self.explanation or "")
        return {"type": "ir.actions.act_window_close"}


class DetentionWizardOption(models.TransientModel):
    """Proyecta las causas pendientes sin conceder lectura directa del historial."""

    _name = "mc.rov.detention.wizard.option"
    _description = "Opción de detención abierta"

    wizard_id = fields.Many2one("mc.rov.detention.wizard", required=True, ondelete="cascade")
    name = fields.Char(required=True)
    interval_key = fields.Char(required=True)
