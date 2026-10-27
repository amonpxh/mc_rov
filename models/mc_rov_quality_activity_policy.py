from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class QualityActivityPolicy(models.Model):
    """Cuenta y calendario explícitos para resolver alertas de Calidad."""

    _name = "mc.rov.quality.activity.policy"
    _description = "Seguimiento de Calidad"
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
    lead_days = fields.Integer(string="Días laborables para resolver", default=1)
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
        "CHECK(lead_days BETWEEN 1 AND 365)",
        "Los plazos deben ser entre 1 y 365 días laborables.",
    )

    @api.model
    def _validate_duration_values(self, values):
        # Integer convertiría True en 1: rechazarlo antes de perder el tipo original.
        if "lead_days" in values:
            days = values["lead_days"]
            if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 365:
                raise ValidationError(
                    _("El plazo debe ser un entero entre 1 y 365 días laborables.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            self._validate_duration_values(values)
        return super().create(vals_list)

    def write(self, values):
        self._validate_duration_values(values)
        return super().write(values)

    @api.constrains("lead_days")
    def _check_days(self):
        # También validar defaults antes de que la restricción SQL exponga una excepción.
        for policy in self:
            if not 1 <= policy.lead_days <= 365:
                raise ValidationError(_("Los plazos deben ser entre 1 y 365 días laborables."))

    @api.depends(
        "company_id",
        "enabled",
        "user_id",
        "calendar_id",
        "employee_id",
        "lead_days",
    )
    def _compute_configuration_message(self):
        # El indicador orienta al coordinador; los eventos revalidan su origen real.
        for policy in self:
            policy.configuration_message = (
                _("Desactivado")
                if not policy.enabled
                else policy._configuration_error() or _("Configuración completa")
            )

    def _configuration_error(self, alert=False):  # pylint: disable=too-many-return-statements
        """No inventar destinatario, permisos o calendario si falta configuración."""
        self.ensure_one()
        if alert and alert.company_id and alert.company_id != self.company_id:
            return _("La alerta pertenece a otra empresa.")
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
                self.env["quality.alert"]
                .with_user(user)
                .with_context(allowed_company_ids=[self.company_id.id])
                .with_company(self.company_id)
            )
            target = target.browse(alert.id) if alert else target
            if not target.has_access("read") or not target.has_access("write"):
                return _("La cuenta no puede consultar y gestionar la alerta.")
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

    def _deadline(self, started_at):
        """Cuenta fechas laborales del calendario explícito de esta política."""
        self.ensure_one()
        return self.env["mc.rov.work.deadline"]._working_date(
            self.calendar_id, self.company_id, started_at, self.lead_days
        )
