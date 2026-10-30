# Se conserva la ruta donde ya se registra este asistente del módulo.
# pylint: disable=unknown-option-value,no-wizard-in-models

from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError


# Solo el asistente validado emite esta identidad; no se puede fabricar desde RPC.
_WORK_ACTIVITY_DEADLINE_AUTH = object()


class McRovActivityAssignmentWizard(models.TransientModel):
    """Reparte acciones pendientes con cambios explícitos y sin cerrar sus documentos."""

    _name = "mc.rov.activity.assignment.wizard"
    _description = "Repartir actividades"

    activity_ids = fields.Many2many("mail.activity", string="Actividades", required=True)
    apply_user = fields.Boolean(string="Cambiar cuenta asignada")
    user_id = fields.Many2one(
        "res.users",
        string="Usuario asignado",
        domain="[('active', '=', True), ('share', '=', False)]",
    )
    apply_employee = fields.Boolean(string="Cambiar empleado asignado")
    employee_id = fields.Many2one(
        "hr.employee.public",
        string="Empleado asignado",
        domain="[('active', '=', True)]",
        help="Dejar vacío al marcar el cambio quita al empleado; no cambia la cuenta.",
    )
    apply_deadline = fields.Boolean(string="Cambiar fecha límite")
    date_deadline = fields.Date(string="Nueva fecha límite")
    reason = fields.Text(string="Motivo", help="Obligatorio al reprogramar una fecha existente.")

    def _assignment_values(self, activities):
        values = {}
        if self.apply_user:
            if not self.user_id or not self.user_id.active or self.user_id.share:
                raise ValidationError(_("Seleccione una cuenta interna activa."))
            values["user_id"] = self.user_id.id
        if self.apply_employee:
            values["mc_employee_id"] = self.employee_id.id or False
        if self.apply_deadline:
            if not self.date_deadline:
                raise UserError(_("Indique la nueva fecha límite."))
            if (
                any(act.date_deadline != self.date_deadline for act in activities)
                and not (self.reason or "").strip()
            ):
                raise UserError(_("Indique el motivo de la reprogramación."))
            values["date_deadline"] = self.date_deadline
        if not values:
            raise UserError(_("Marque al menos un campo para cambiar."))
        return values

    def _validate_targets(self, activities):
        for activity in activities:
            company = activity._mc_assignment_company({})
            if self.apply_user and company and company not in self.user_id.company_ids:
                raise ValidationError(_("La cuenta debe tener acceso a la empresa del documento."))
            if self.apply_employee:
                activity._mc_validate_employee(
                    self.employee_id.id,
                    {},
                    new_assignment=self.employee_id.id != activity.mc_employee_id.id,
                )

    def _assignment_note(self, activity):
        changes = []
        if self.apply_user:
            changes.append(
                _(
                    "Cuenta: %(old)s -> %(new)s",
                    old=activity.user_id.display_name,
                    new=self.user_id.display_name,
                )
            )
        if self.apply_employee:
            changes.append(
                _(
                    "Empleado: %(old)s -> %(new)s",
                    old=activity.mc_employee_display,
                    new=self.employee_id.display_name or _("Sin asignar"),
                )
            )
        if self.apply_deadline:
            changes.append(
                _("Fecha: %(old)s -> %(new)s", old=activity.date_deadline, new=self.date_deadline)
            )
        text = _(
            "Actividad: %(activity)s. %(changes)s",
            activity=activity.summary or activity.activity_type_id.display_name,
            changes="; ".join(changes),
        )
        if (self.reason or "").strip():
            text += _(". Motivo: %s", self.reason.strip())
        return Markup("<p>%s</p>") % text

    def action_apply(self):
        self.ensure_one()
        # Revalidar al guardar: abrir antes no garantiza permiso ni estado actual.
        with self.env.cr.savepoint():
            activities = self.env["mc.rov.work.assignment"]._assignment_activities(
                self.activity_ids.ids
            )
            values = self._assignment_values(activities)
            self._validate_targets(activities)
            entries = []
            for activity in activities:
                source = (
                    self.env[activity.res_model].browse(activity.res_id)
                    if activity.res_model and activity.res_id
                    else False
                )
                body = self._assignment_note(activity)
                if source and hasattr(source, "message_post"):
                    entries.append((source, body))
                else:
                    # Una actividad libre carece de chatter: conservar el motivo
                    # en su nota, bajo la cuenta autora, dentro de la misma transaccion.
                    author = Markup("<p>%s</p>") % _(
                        "Cuenta autora: %s", self.env.user.display_name
                    )
                    activity.write({"note": Markup(activity.note or "") + author + body})
            if "date_deadline" in values:
                authorization = (
                    _WORK_ACTIVITY_DEADLINE_AUTH,
                    self.env.uid,
                    tuple(activities.ids),
                    fields.Date.to_date(values["date_deadline"]),
                    (self.reason or "").strip(),
                )
                activities = activities.with_context(
                    _mc_activity_deadline_authorization=authorization
                )
            activities.write(values)
            for source, body in entries:
                source.message_post(body=body, subtype_xmlid="mail.mt_note")
        return {"type": "ir.actions.act_window_close"}
