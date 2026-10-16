from datetime import timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ManufacturingActivityPolicy(models.Model):
    """Cuenta y plazo comercial de fabricación, sin inferirlos de horas de taller."""

    _name = "mc.rov.manufacturing.activity.policy"
    _description = "Seguimiento de fabricación"
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
        help="Opcional. No se deduce del usuario ni de quien ejecuta una operación.",
    )
    calendar_id = fields.Many2one(
        "resource.calendar",
        string="Calendario y zona horaria",
        check_company=True,
        help="Su zona determina la fecha local. Los días corridos incluyen fines de semana y festivos.",
    )
    lead_days = fields.Integer(string="Plazo máximo (días corridos)", default=28)
    configuration_message = fields.Char(
        string="Configuración",
        compute="_compute_configuration_message",
        compute_sudo=False,
    )

    _company_unique = models.Constraint(
        "UNIQUE(company_id)", "Solo puede existir una política de fabricación por empresa."
    )
    _positive_days = models.Constraint(
        "CHECK(lead_days BETWEEN 1 AND 365)", "El plazo debe ser entre 1 y 365 días corridos."
    )

    @api.model
    def _validate_duration_values(self, values):
        # Antes de que Integer convierta True en 1, rechazar un plazo de tipo incorrecto.
        if "lead_days" in values:
            days = values["lead_days"]
            if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 365:
                raise ValidationError(
                    _("El plazo debe ser un entero entre 1 y 365 días corridos.")
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
        # Explicar también los defaults inválidos antes de alcanzar la restricción SQL.
        for policy in self:
            if not 1 <= policy.lead_days <= 365:
                raise ValidationError(_("El plazo debe ser entre 1 y 365 días corridos."))

    @api.depends("company_id", "enabled", "user_id", "employee_id", "calendar_id", "lead_days")
    def _compute_configuration_message(self):
        # Es un diagnóstico de configuración, no una afirmación de trabajo ya generado.
        for policy in self:
            policy.configuration_message = (
                _("Desactivado")
                if not policy.enabled
                else policy._configuration_error() or _("Configuración completa")
            )

    # Cada rechazo devuelve una causa accionable sin exponer datos del origen al destinatario.
    def _configuration_error(self, production=False):  # pylint: disable=too-many-return-statements
        """Verificar empresa y acceso real del destinatario antes de generar trabajo."""
        self.ensure_one()
        if production and production.company_id != self.company_id:
            return _("La fabricación pertenece a otra empresa.")
        user = self.user_id
        if not user or not user.active or user.share:
            return _("Seleccione una cuenta interna activa.")
        if self.company_id not in user.company_ids:
            return _("La cuenta no tiene acceso a esta empresa.")
        calendar = self.calendar_id
        if not calendar or not calendar.tz:
            return _("Seleccione un calendario con zona horaria definida.")
        if calendar.company_id and calendar.company_id != self.company_id:
            return _("El calendario pertenece a otra empresa.")
        try:
            # La cuenta compartida no hereda las empresas activas de quien confirma la MO.
            target = (
                self.env["mrp.production"]
                .with_user(user)
                .with_context(allowed_company_ids=[self.company_id.id])
                .with_company(self.company_id)
            )
            target = target.browse(production.id) if production else target
            if not target.has_access("read") or not target.has_access("write"):
                return _("La cuenta no puede consultar y gestionar la fabricación.")
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

    def _deadline(self, started_at, explicit_deadline=False):
        """Sumar fechas locales; una fecha explícita anterior no puede ampliarse sola."""
        self.ensure_one()
        calendar = self.calendar_id
        if not calendar or not calendar.tz or calendar.tz not in pytz.all_timezones_set:
            raise ValidationError(_("Seleccione un calendario con zona horaria válida."))
        if calendar.company_id and calendar.company_id != self.company_id:
            raise ValidationError(_("El calendario pertenece a otra empresa."))
        self._validate_duration_values({"lead_days": self.lead_days})
        started_at = fields.Datetime.to_datetime(started_at)
        if not started_at:
            raise ValidationError(_("Falta el instante de confirmación de la fabricación."))
        local_policy = self.with_context(tz=calendar.tz)
        deadline = fields.Datetime.context_timestamp(local_policy, started_at).date() + timedelta(
            days=self.lead_days
        )
        if explicit_deadline:
            explicit_deadline = fields.Datetime.to_datetime(explicit_deadline)
            local_limit = fields.Datetime.context_timestamp(local_policy, explicit_deadline).date()
            deadline = min(deadline, local_limit)
        return deadline
