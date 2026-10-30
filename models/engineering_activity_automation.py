from markupsafe import Markup

from odoo import _, models
from odoo.exceptions import ValidationError


# Un cliente RPC no puede fabricar esta identidad para omitir los observadores.
_ENGINEERING_INTERNAL = object()


class EngineeringActivityAutomation(models.AbstractModel):
    """Crea tareas propias sobre un ECO autorizado sin asumir su aprobación nativa."""

    _name = "mc.rov.engineering.activity.automation"
    _description = "Automatización de actividades de ingeniería"

    def _actor_eco(self, eco):
        return eco.with_env(self.env).with_context(_mc_engineering_capture=_ENGINEERING_INTERNAL)

    def _in_scope(self, eco):
        eco = self._actor_eco(eco)
        eco.ensure_one()
        if not eco.has_access("read"):
            return False
        if not eco.company_id or eco.company_id not in self.env.companies:
            return False
        product = eco.product_tmpl_id
        if not product or not product.has_access("read"):
            return False
        if product.company_id and product.company_id != eco.company_id:
            return False
        root = self.env["stock.lot"]._get_rov_root_category()
        return bool(
            root
            and self.env["product.category"].search_count(
                [("id", "=", product.categ_id.id), ("id", "child_of", root.id)]
            )
        )

    def _applicable(self, eco):
        """La bandera de etapa sola no garantiza aprobación ni ausencia de bloqueo."""
        eco = self._actor_eco(eco)
        eco.ensure_one()
        return bool(
            eco.active
            and eco.state in ("confirmed", "progress")
            and eco.allow_apply_change
            and eco.allow_change_stage
            and eco.kanban_state != "blocked"
        )

    def _configured_policy(self, eco, stage, explain=False):
        eco = self._actor_eco(eco)
        if not eco.has_access("read") or not eco.company_id:
            return False
        if eco.company_id not in self.env.companies:
            return False
        policy = (
            self.env["mc.rov.engineering.activity.policy"]
            .sudo()
            .search([("company_id", "=", eco.company_id.id)], limit=1)
        )
        if (
            not policy
            or not policy.enabled
            or not self.env["mc.rov.automation.control"]._creation_enabled(eco.company_id)
            or not self._in_scope(eco)
        ):
            return False
        reason = policy._configuration_error(eco, stage)
        if reason:
            if explain:
                eco.message_post(body=_("Seguimiento automático no generado: %s", reason))
            return False
        return policy

    def _start(self, eco, stage, occurred_at):
        """El ciclo captura un solo aniversario y cada evento una única actividad propia."""
        if stage not in ("prepare", "apply"):
            raise ValidationError(_("La etapa de ingeniería no es válida."))
        if isinstance(eco.id, bool) or not isinstance(eco.id, int) or eco.id <= 0:
            return False
        eco = self._actor_eco(eco)
        if not eco.active or eco.state == "done":
            return False
        if stage != ("apply" if self._applicable(eco) else "prepare"):
            return False
        policy = self._configured_policy(eco, stage, explain=True)
        if not policy:
            return False
        self.env["mc.rov.engineering.activity.lifecycle"]._capture(eco)
        cycles = self.env["mc.rov.engineering.activity.cycle"].sudo()
        cycle = cycles.search([("eco_id", "=", eco.id)], limit=1)
        if not cycle:
            deadline = policy._deadline(eco.create_date)
            cycle = cycles.create(
                {
                    "company_id": eco.company_id.id,
                    "eco_id": eco.id,
                    "policy_id": policy.id,
                    "eco_created_at": eco.create_date,
                    "started_at": occurred_at,
                    "original_deadline": deadline,
                    "current_deadline": deadline,
                    "deadline_tz": policy.tz,
                    "lead_years": policy.lead_years,
                    "observed_stage": stage,
                    "event_sequence": 1,
                }
            )
        if cycle.company_id != eco.company_id or cycle.observed_stage != stage:
            raise ValidationError(_("La etapa o empresa no coincide con el ciclo de ingeniería."))
        runs = self.env["mc.rov.engineering.activity.run"].sudo()
        existing = runs.search(
            [
                ("cycle_id", "=", cycle.id),
                ("event", "=", cycle.event_sequence),
                ("stage", "=", stage),
            ],
            limit=1,
        )
        if existing:
            return existing
        user = policy.prepare_user_id if stage == "prepare" else policy.apply_user_id
        employee = policy.prepare_employee_id if stage == "prepare" else policy.apply_employee_id
        activity = (
            self.env["mail.activity"]
            .sudo()
            .with_company(eco.company_id)
            .create(
                {
                    "res_model_id": self.env["ir.model"]._get_id("mrp.eco"),
                    "res_id": eco.id,
                    "activity_type_id": self.env.ref(
                        "mc_rov.activity_type_engineering_" + stage
                    ).id,
                    "summary": (
                        _("Preparar cambio de ingeniería")
                        if stage == "prepare"
                        else _("Aplicar cambio de ingeniería")
                    ),
                    "note": Markup('<p><a href="/odoo/mrp.eco/%s">%s</a></p>')
                    % (eco.id, eco.display_name),
                    "user_id": user.id,
                    "mc_employee_id": employee.id or False,
                    "date_deadline": cycle.current_deadline,
                }
            )
        )
        return runs.create(
            {
                "company_id": eco.company_id.id,
                "cycle_id": cycle.id,
                "event": cycle.event_sequence,
                "stage": stage,
                "activity_id": activity.id,
                "started_at": occurred_at,
                "original_deadline": cycle.original_deadline,
                "current_deadline": cycle.current_deadline,
            }
        )
