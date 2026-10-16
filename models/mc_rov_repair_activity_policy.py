from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class RepairActivityPolicy(models.Model):
    """Configuración explícita por empresa para seguir diagnóstico y reparación."""

    _name = "mc.rov.repair.activity.policy"
    _description = "Seguimiento de reparaciones"
    _rec_name = "company_id"
    _check_company_auto = True

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
    )
    enabled = fields.Boolean(string="Activado", default=True)
    user_id = fields.Many2one("res.users", string="Cuenta destinataria", ondelete="restrict")
    employee_id = fields.Many2one(
        "hr.employee.public",
        string="Empleado asignado",
        check_company=True,
        help="Opcional. No se deduce de la cuenta ni del técnico de la revisión.",
    )
    calendar_id = fields.Many2one(
        "resource.calendar",
        string="Calendario laboral",
        check_company=True,
        help="Elegir el calendario de empresa verificado; no se modifica al instalar.",
    )
    diagnosis_days = fields.Integer(string="Días laborables de diagnóstico", default=2)
    repair_days = fields.Integer(string="Días laborables de reparación", default=2)
    configuration_message = fields.Char(
        string="Configuración",
        compute="_compute_configuration_message",
        compute_sudo=False,
    )

    _company_unique = models.Constraint(
        "UNIQUE(company_id)",
        "Solo puede existir una política por empresa.",
    )
    _positive_days = models.Constraint(
        "CHECK(diagnosis_days BETWEEN 1 AND 365 AND repair_days BETWEEN 1 AND 365)",
        "Los plazos deben ser entre 1 y 365 días laborables.",
    )

    @api.constrains("diagnosis_days", "repair_days")
    def _check_days(self):
        # Validar antes del flush permite explicar el error sin exponer SQL al usuario.
        for policy in self:
            if not 1 <= policy.diagnosis_days <= 365 or not 1 <= policy.repair_days <= 365:
                raise ValidationError(_("Los plazos deben ser entre 1 y 365 días laborables."))

    @api.depends(
        "company_id",
        "enabled",
        "user_id",
        "calendar_id",
        "employee_id",
        "diagnosis_days",
        "repair_days",
    )
    def _compute_configuration_message(self):
        # El indicador orienta al coordinador; los eventos revalidan su origen real.
        for policy in self:
            policy.configuration_message = (
                _("Desactivado")
                if not policy.enabled
                else policy._configuration_error() or _("Configuración completa")
            )

    def _configuration_error(self, order=False):  # pylint: disable=too-many-return-statements
        """No inventar destinatario, permisos o calendario si falta configuración."""
        self.ensure_one()
        if order and order.company_id != self.company_id:
            return _("La orden pertenece a otra empresa.")
        user = self.user_id
        if not user or not user.active or user.share:
            return _("Seleccione una cuenta interna activa.")
        if self.company_id not in user.company_ids:
            return _("La cuenta no tiene acceso a esta empresa.")
        calendar = self.calendar_id
        if not calendar or not calendar.tz or calendar.flexible_hours:
            return _("Seleccione un calendario con jornadas y zona horaria definidas.")
        if calendar.company_id and calendar.company_id != self.company_id:
            return _("El calendario pertenece a otra empresa.")
        if not calendar.attendance_ids.filtered(
            lambda line: not line.display_type
            and line.day_period != "lunch"
            and line.hour_to > line.hour_from
        ):
            return _("El calendario no contiene jornadas laborables.")
        try:
            # El destinatario no hereda las empresas activas de quien dispara el evento.
            target = (
                self.env["repair.order"]
                .with_user(user)
                .with_context(allowed_company_ids=[self.company_id.id])
                .with_company(self.company_id)
            )
            target = target.browse(order.id) if order else target
            if not target.has_access("read") or not target.has_access("write"):
                return _("La cuenta no puede consultar y gestionar la orden.")
            if self.employee_id:
                employee = (
                    self.env["hr.employee.public"]
                    .with_user(user)
                    .with_context(allowed_company_ids=[self.company_id.id])
                    .with_company(self.company_id)
                    .search(
                        [
                            ("id", "=", self.employee_id.id),
                            ("company_id", "=", self.company_id.id),
                            ("active", "=", True),
                        ],
                        limit=1,
                    )
                )
                if not employee:
                    return _("El empleado no está activo o no es accesible en esta empresa.")
        except AccessError:
            return _("La cuenta no tiene permisos suficientes para la asignación.")
        return False

    def _deadline(self, started_at, days):
        """Conserva los plazos del piloto mediante el cálculo laboral compartido."""
        self.ensure_one()
        return self.env["mc.rov.work.deadline"]._working_date(
            self.calendar_id, self.company_id, started_at, days
        )
