from datetime import datetime

from dateutil.relativedelta import relativedelta
import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class EngineeringActivityPolicy(models.Model):
    """Plazo total de ingeniería y destinatarios explícitos, sin configurar aprobadores."""

    _name = "mc.rov.engineering.activity.policy"
    _description = "Seguimiento de ingeniería"
    _rec_name = "company_id"
    _check_company_auto = True

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
    )
    enabled = fields.Boolean(string="Activado", default=False)
    prepare_user_id = fields.Many2one(
        "res.users", string="Cuenta para preparar el cambio", ondelete="restrict"
    )
    apply_user_id = fields.Many2one(
        "res.users", string="Cuenta para aplicar el cambio", ondelete="restrict"
    )
    prepare_employee_id = fields.Many2one(
        "hr.employee.public",
        string="Empleado de preparación",
        check_company=True,
        help="Opcional; se reparte después sin deducirlo de la cuenta o el autor.",
    )
    apply_employee_id = fields.Many2one(
        "hr.employee.public",
        string="Empleado de aplicación",
        check_company=True,
        help="Opcional; no sustituye a los aprobadores nativos del cambio.",
    )
    lead_years = fields.Integer(string="Años corridos totales", default=1)
    tz = fields.Selection(
        [(zone, zone) for zone in pytz.common_timezones],
        string="Zona horaria operativa",
        help="El aniversario usa la fecha local de creación; no modifica el calendario de empresa.",
    )
    configuration_message = fields.Char(
        string="Configuración", compute="_compute_configuration_message", compute_sudo=False
    )

    _company_unique = models.Constraint(
        "UNIQUE(company_id)", "Solo puede existir una política de ingeniería por empresa."
    )
    _positive_years = models.Constraint(
        "CHECK(lead_years > 0)", "El plazo debe ser un número positivo de años corridos."
    )

    @api.model
    def _validate_duration_values(self, values):
        # Validar antes de que Integer convierta True o una fracción en otro valor.
        if "lead_years" in values:
            years = values["lead_years"]
            if isinstance(years, bool) or not isinstance(years, int) or years <= 0:
                raise ValidationError(_("El plazo debe ser un entero positivo de años corridos."))

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            self._validate_duration_values(values)
        return super().create(vals_list)

    def write(self, values):
        self._validate_duration_values(values)
        return super().write(values)

    @api.constrains("lead_years")
    def _check_years(self):
        for policy in self:
            if policy.lead_years <= 0:
                raise ValidationError(_("El plazo debe ser un entero positivo de años corridos."))

    @api.depends(
        "company_id",
        "enabled",
        "prepare_user_id",
        "apply_user_id",
        "prepare_employee_id",
        "apply_employee_id",
        "lead_years",
        "tz",
    )
    def _compute_configuration_message(self):
        for policy in self:
            policy.configuration_message = (
                _("Desactivado")
                if not policy.enabled
                else policy._configuration_error(stage="prepare")
                or policy._configuration_error(stage="apply")
                or _("Configuración completa")
            )

    def _configuration_error(
        self, eco=False, stage="prepare"
    ):  # pylint: disable=too-many-return-statements
        """Revalidar empresa y acceso del destinatario sin heredar el contexto del actor."""
        self.ensure_one()
        if stage not in ("prepare", "apply"):
            raise ValidationError(_("La etapa de ingeniería no es válida."))
        if eco:
            eco.ensure_one()
            if not eco.company_id or eco.company_id != self.company_id:
                return _("El cambio debe pertenecer a la empresa de esta política.")
        if not self.tz:
            return _("Seleccione una zona horaria operativa.")
        user = self.prepare_user_id if stage == "prepare" else self.apply_user_id
        employee = self.prepare_employee_id if stage == "prepare" else self.apply_employee_id
        if not user or not user.active or user.share:
            return _("Seleccione una cuenta interna activa para esta etapa.")
        if self.company_id not in user.company_ids:
            return _("La cuenta no tiene acceso a esta empresa.")
        try:
            target = (
                self.env["mrp.eco"]
                .with_user(user)
                .with_context(allowed_company_ids=[self.company_id.id])
                .with_company(self.company_id)
            )
            target = target.browse(eco.id) if eco else target
            if not target.has_access("read") or not target.has_access("write"):
                return _("La cuenta no puede consultar y gestionar el cambio de ingeniería.")
            if employee:
                public = (
                    self.env["hr.employee.public"]
                    .with_user(user)
                    .with_context(allowed_company_ids=[self.company_id.id])
                    .with_company(self.company_id)
                    .search(
                        [
                            ("id", "=", employee.id),
                            ("company_id", "=", self.company_id.id),
                            ("active", "=", True),
                        ],
                        limit=1,
                    )
                )
                if not public:
                    return _("El empleado no está activo o no es accesible en esta empresa.")
        except AccessError:
            return _("La cuenta no tiene permisos suficientes para la asignación.")
        return False

    def _deadline(self, created_at):
        """Un aniversario local: el 29 de febrero pasa al 28 cuando no hay bisiesto."""
        self.ensure_one()
        if not self.tz or self.lead_years <= 0:
            raise ValidationError(_("Falta una zona horaria o un plazo anual válido."))
        # El conversor nativo rechaza datetimes con zona; conservar su instante.
        if not isinstance(created_at, datetime):
            created_at = fields.Datetime.to_datetime(created_at)
        if not created_at:
            raise ValidationError(_("Falta el instante de creación del cambio."))
        instant = created_at if created_at.tzinfo else pytz.utc.localize(created_at)
        try:
            local_date = instant.astimezone(pytz.timezone(self.tz)).date()
            return local_date + relativedelta(years=self.lead_years)
        except (ValueError, OverflowError) as error:
            raise ValidationError(_("El plazo anual supera las fechas admitidas.")) from error
