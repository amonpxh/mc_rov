from datetime import datetime

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class InventoryActivityPolicy(models.Model):
    """Reglas explícitas por operación; nunca crea responsables o compras implícitos."""

    _name = "mc.rov.inventory.activity.policy"
    _description = "Seguimiento de inventario"
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
    calendar_id = fields.Many2one(
        "resource.calendar",
        string="Calendario laboral",
        check_company=True,
        help="Calendario explícito; esta configuración no modifica sus jornadas.",
    )
    lead_days = fields.Integer(string="Días laborables", default=3)
    rule_ids = fields.One2many(
        "mc.rov.inventory.activity.rule", "policy_id", string="Operaciones seleccionadas"
    )
    configuration_message = fields.Char(
        string="Configuración", compute="_compute_configuration_message", compute_sudo=False
    )

    _company_unique = models.Constraint(
        "UNIQUE(company_id)", "Solo puede existir una política de inventario por empresa."
    )
    _positive_days = models.Constraint(
        "CHECK(lead_days BETWEEN 1 AND 365)", "El plazo debe estar entre 1 y 365 días laborables."
    )

    @api.model
    def _validate_duration_values(self, values):
        # Validar antes de la coerción nativa de Integer, que perdería True/fracciones.
        if "lead_days" in values:
            days = values["lead_days"]
            if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 365:
                raise ValidationError(_("El plazo debe ser un entero entre 1 y 365 días."))

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            self._validate_duration_values(values)
        return super().create(vals_list)

    def write(self, values):
        self._validate_duration_values(values)
        return super().write(values)

    @api.depends(
        "enabled",
        "company_id",
        "calendar_id",
        "lead_days",
        "rule_ids",
        "rule_ids.picking_type_id",
        "rule_ids.user_id",
        "rule_ids.employee_id",
    )
    def _compute_configuration_message(self):
        # El indicador ayuda a configurar; cada evento revalidará su documento real.
        for policy in self:
            policy.configuration_message = (
                _("Desactivado")
                if not policy.enabled
                else policy._configuration_error() or _("Configuración completa")
            )

    def _rule_for(self, picking):
        self.ensure_one()
        if not picking or picking.company_id != self.company_id:
            return self.env["mc.rov.inventory.activity.rule"]
        return self.rule_ids.filtered(
            lambda rule: rule.picking_type_id == picking.picking_type_id
        )[:1]

    # Cada salida conserva una explicación concreta del requisito pendiente.
    # pylint: disable=too-many-return-statements
    def _configuration_error(self, picking=False):
        """Configurar una regla no concede acceso al origen a su destinatario."""
        self.ensure_one()
        if picking and picking.company_id != self.company_id:
            return _("La operación pertenece a otra empresa.")
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
        rules = self._rule_for(picking) if picking else self.rule_ids
        if not rules:
            return _("Seleccione los tipos de operación que desea seguir.")
        for rule in rules:
            error = rule._configuration_error(picking)
            if error:
                return error
        return False

    @api.model
    def _utc_instant(self, value):
        instant = value if isinstance(value, datetime) else fields.Datetime.to_datetime(value)
        if not instant:
            raise ValidationError(_("Falta el instante de confirmación de la operación."))
        return instant.astimezone(pytz.utc).replace(tzinfo=None) if instant.tzinfo else instant

    def _deadline(self, confirmed_at, scheduled_at=False, explicit_deadline=False):
        """Ancla inicial UTC, sin ampliar un compromiso nativo anterior."""
        self.ensure_one()
        anchor = self._utc_instant(confirmed_at)
        if scheduled_at:
            anchor = max(anchor, self._utc_instant(scheduled_at))
        deadline = self.env["mc.rov.work.deadline"]._working_date(
            self.calendar_id, self.company_id, anchor, self.lead_days
        )
        if explicit_deadline:
            native = pytz.utc.localize(self._utc_instant(explicit_deadline))
            native_day = native.astimezone(pytz.timezone(self.calendar_id.tz)).date()
            deadline = min(deadline, native_day)
        return deadline


class InventoryActivityRule(models.Model):
    """Una cuenta por tipo seleccionado; pertenencia y derechos se validan por empresa."""

    _name = "mc.rov.inventory.activity.rule"
    _description = "Regla de seguimiento de inventario"
    _rec_name = "picking_type_id"
    _check_company_auto = True

    policy_id = fields.Many2one(
        "mc.rov.inventory.activity.policy", required=True, ondelete="cascade", check_company=True
    )
    company_id = fields.Many2one(related="policy_id.company_id", store=True, index=True)
    picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Tipo de operación",
        required=True,
        check_company=True,
        ondelete="restrict",
    )
    user_id = fields.Many2one("res.users", string="Cuenta destinataria", ondelete="restrict")
    employee_id = fields.Many2one(
        "hr.employee.public",
        string="Empleado asignado",
        check_company=True,
        help="Opcional; se puede repartir después. No se deduce de la cuenta autora.",
    )

    _type_unique = models.Constraint(
        "UNIQUE(policy_id, picking_type_id)", "Este tipo de operación ya está seleccionado."
    )

    # Cada salida conserva una explicación concreta del requisito pendiente.
    # pylint: disable=too-many-return-statements
    def _configuration_error(self, picking=False):
        self.ensure_one()
        kind = self.picking_type_id
        if kind.company_id != self.company_id or kind.code not in (
            "incoming",
            "outgoing",
            "internal",
        ):
            return _("Seleccione una recepción, entrega o transferencia de esta empresa.")
        if picking and (picking.company_id != self.company_id or picking.picking_type_id != kind):
            return _("La regla no corresponde a esta operación.")
        user = self.user_id
        if not user or not user.active or user.share:
            return _("Seleccione una cuenta interna activa.")
        if self.company_id not in user.company_ids:
            return _("La cuenta no tiene acceso a esta empresa.")
        try:
            # El contexto del actor nunca amplía las empresas del destinatario.
            target = (
                self.env["stock.picking"]
                .with_user(user)
                .with_context(allowed_company_ids=self.company_id.ids)
                .with_company(self.company_id)
            )
            target = target.browse(picking.id) if picking else target
            if not target.has_access("read") or not target.has_access("write"):
                return _("La cuenta no puede consultar y gestionar la operación.")
            recipient_kind = target.env["stock.picking.type"].browse(kind.id)
            if not recipient_kind.has_access("read"):
                return _("La cuenta no tiene acceso al tipo de operación.")
            if self.employee_id:
                employee = target.env["hr.employee.public"].search(
                    [
                        ("id", "=", self.employee_id.id),
                        ("company_id", "=", self.company_id.id),
                        ("active", "=", True),
                    ],
                    limit=1,
                )
                if not employee:
                    return _("El empleado no está activo o no es accesible en esta empresa.")
        except AccessError:
            return _("La cuenta no tiene permisos suficientes para esta asignación.")
        return False
