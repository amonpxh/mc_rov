from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.tools import SQL

_SPLIT_TOKEN = object()
_PARENT_FIELD = "mc_manufacturing_parent_run_key"


class ManufacturingActivityAutomation(models.AbstractModel):
    """Crea un pendiente por confirmación sin dirigir la fabricación nativa."""

    _name = "mc.rov.manufacturing.activity.automation"
    _description = "Automatización de actividades de fabricación"

    def _start(self, production, started_at, parent=False):
        production.ensure_one()
        production.check_access("write")
        root = self.env["stock.lot"]._get_rov_root_category()
        if not root or not self.env["product.category"].search_count(
            [("id", "=", production.product_id.categ_id.id), ("id", "child_of", root.id)]
        ):
            return False
        policy = (
            self.env["mc.rov.manufacturing.activity.policy"]
            .sudo()
            .search([("company_id", "=", production.company_id.id)], limit=1)
        )
        if not self.env["mc.rov.automation.control"]._creation_enabled(production.company_id) or (
            policy and not policy.enabled
        ):
            return False
        reason = (
            policy._configuration_error(production)
            if policy
            else _("Configure cuenta y calendario en Seguimiento de fabricación.")
        )
        if reason:
            production.message_post(body=_("Seguimiento automático no generado: %s", reason))
            return False
        runs = self.env["mc.rov.manufacturing.activity.run"].sudo()
        existing = runs.search([("production_id", "=", production.id)], limit=1)
        if existing:
            return existing
        deadline = policy._deadline(started_at, production.date_deadline)
        if parent:
            # Una división hereda también una reprogramación manual del pendiente original.
            deadline = (
                parent.activity_id.date_deadline
                or parent.current_deadline
                or parent.original_deadline
            )
            if production.date_deadline:
                explicit = fields.Datetime.context_timestamp(
                    policy.with_context(tz=policy.calendar_id.tz), production.date_deadline
                ).date()
                deadline = min(deadline, explicit)
        activity = (
            self.env["mail.activity"]
            .sudo()
            .with_company(production.company_id)
            .create(
                {
                    "res_model_id": self.env["ir.model"]._get_id("mrp.production"),
                    "res_id": production.id,
                    "activity_type_id": self.env.ref(
                        "mc_rov.activity_type_manufacturing_complete"
                    ).id,
                    "summary": _("Completar fabricación"),
                    "note": Markup('<p><a href="/odoo/mrp.production/%s">%s</a></p>')
                    % (production.id, production.display_name),
                    "user_id": policy.user_id.id,
                    "mc_employee_id": policy.employee_id.id or False,
                    "date_deadline": deadline,
                }
            )
        )
        return runs.create(
            {
                "company_id": production.company_id.id,
                "production_id": production.id,
                "cycle": 1,
                "parent_run_id": parent.id if parent else False,
                "activity_id": activity.id,
                "started_at": started_at,
                "original_deadline": deadline,
                "current_deadline": deadline,
                "calendar_id": policy.calendar_id.id,
                "calendar_tz": policy.calendar_id.tz,
            }
        )


class ManufacturingProductionAutomation(models.Model):
    """Observa confirmaciones y divisiones reales; el compute de estado queda nativo."""

    _inherit = "mrp.production"

    # Solo la división nativa conoce el padre exacto; una copia común no lo hereda.
    # Clave interna, sin Many2one público que intente leer nombres del historial privado.
    mc_manufacturing_parent_run_key = fields.Integer(
        readonly=True,
        copy=False,
        groups="base.group_system",
    )

    @api.model_create_multi
    def create(self, vals_list):
        internal = self.env.context.get("_mc_manufacturing_split") is _SPLIT_TOKEN
        if not internal and any(_PARENT_FIELD in values for values in vals_list):
            raise AccessError(_("El origen del seguimiento se administra internamente."))
        if internal:
            return super().create(vals_list)
        # No escribir ni siquiera False en un campo técnico desde una cuenta Taller.
        # Retirar el default RPC evita falsificar el padre sin elevar permisos del create.
        context = {
            key: value
            for key, value in self.env.context.items()
            if key != "default_" + _PARENT_FIELD
        }
        return super(ManufacturingProductionAutomation, self.with_context(context)).create(
            vals_list
        )

    def write(self, vals):
        if _PARENT_FIELD in vals:
            raise AccessError(_("El origen del seguimiento se administra internamente."))
        return super().write(vals)

    def _mc_lock_manufacturing(self):
        self.check_access("write")
        self.flush_recordset(["state"])
        self.env.cr.execute(
            SQL(
                "SELECT id FROM %s WHERE id IN %s ORDER BY id FOR UPDATE",
                SQL.identifier(self._table),
                tuple(sorted(self.ids)),
            )
        )
        self.invalidate_recordset(["state"])

    def action_confirm(self):
        persistent = self.filtered(lambda record: isinstance(record.id, int) and record.id > 0)
        if not persistent:
            return super().action_confirm()
        persistent._mc_lock_manufacturing()
        drafts = persistent.filtered(lambda record: record.state == "draft")
        result = super().action_confirm()
        service = self.env["mc.rov.manufacturing.activity.automation"]
        for production in drafts.filtered(lambda record: record.state == "confirmed"):
            service._start(production, fields.Datetime.now())
        return result

    def _get_backorder_mo_vals(self):
        values = super()._get_backorder_mo_vals()
        if self.env.context.get("_mc_manufacturing_split") is _SPLIT_TOKEN:
            run = (
                self.env["mc.rov.manufacturing.activity.run"]
                .sudo()
                .search([("production_id", "=", self.id)], order="cycle desc", limit=1)
            )
            values[_PARENT_FIELD] = run.id or False
        return values

    def _split_productions(self, *args, **kwargs):
        if not self:
            return super()._split_productions(*args, **kwargs)
        self._mc_lock_manufacturing()
        # Un objeto de Python no se puede falsificar mediante contexto RPC/JSON.
        scoped = self.with_context(_mc_manufacturing_split=_SPLIT_TOKEN)
        result = super(ManufacturingProductionAutomation, scoped)._split_productions(
            *args, **kwargs
        )
        # No devolver el token en entornos que puedan acabar en acciones para el navegador.
        result = result.with_env(self.env)
        service = self.env["mc.rov.manufacturing.activity.automation"]
        for child in result - self:
            parent = (
                self.env["mc.rov.manufacturing.activity.run"]
                .sudo()
                .browse(child.sudo().mc_manufacturing_parent_run_key)
            )
            if parent and child.state == "confirmed":
                service._start(child, fields.Datetime.now(), parent=parent)
        return result
