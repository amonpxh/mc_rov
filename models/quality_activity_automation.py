from markupsafe import Markup

from odoo import _, models
from odoo.exceptions import AccessError
from odoo.tools import SQL


class QualityActivityAutomation(models.AbstractModel):
    """Delimita alertas del equipo por relaciones explícitas y permisos del actor."""

    _name = "mc.rov.quality.activity.automation"
    _description = "Automatización de actividades de Calidad"

    def _in_scope(self, alert):
        """No inferir equipos desde el nombre del componente o el autor del chequeo."""
        alert = alert.with_env(self.env)
        alert.ensure_one()
        alert.check_access("read")
        company = alert.company_id
        if company not in self.env.companies:
            raise AccessError(_("La alerta pertenece a una empresa no activa."))

        def authorize(records):
            if not records:
                return records
            records.check_access("read")
            if "company_id" in records._fields and any(
                record.company_id and record.company_id != company for record in records
            ):
                raise AccessError(_("El origen de la alerta pertenece a otra empresa."))
            return records

        products = authorize(alert.product_id)
        templates = authorize(alert.product_tmpl_id)
        lots = authorize(alert.lot_ids)
        productions = authorize(alert.production_id)
        repairs = authorize(alert.repair_id)
        # Autorizar cada enlace antes de leer sus productos, sin sudo ni ampliar empresas.
        products |= authorize(lots.product_id | productions.product_id | repairs.product_id)
        templates |= authorize(products.product_tmpl_id)
        root = self.env["stock.lot"]._get_rov_root_category()
        return bool(
            root
            and self.env["product.category"].search_count(
                [("id", "in", templates.categ_id.ids), ("id", "child_of", root.id)]
            )
        )

    def _start(self, alert, started_at, reopening=False):
        """Inicia solo un evento nuevo autorizado; una edición no reconstruye pendientes."""
        if not isinstance(alert.id, int) or alert.id <= 0:
            return False
        service = self.with_user(self.env.uid)
        alert = alert.with_env(service.env)
        lifecycle = service.env["mc.rov.quality.activity.lifecycle"]
        lifecycle._capture(alert)
        if alert.stage_id.done:
            return False
        # FOR UPDATE por sí solo no renueva una instantánea REPEATABLE READ.
        # Crear una versión de la fila fuerza el retry completo del segundo inicio,
        # antes de que intente duplicar seguidores o el ciclo con una vista antigua.
        service.env.cr.execute(
            SQL("UPDATE quality_alert SET write_date = write_date WHERE id = %s", alert.id)
        )
        runs = service.env["mc.rov.quality.activity.run"].sudo()
        latest = runs.search([("alert_id", "=", alert.id)], order="cycle desc", limit=1)
        if latest and (latest.outcome == "pending" or not reopening):
            return latest
        policy = (
            service.env["mc.rov.quality.activity.policy"]
            .sudo()
            .search([("company_id", "=", alert.company_id.id)], limit=1)
        )
        # Sin política no hay seguimiento que autorizar ni destinatario que inventar.
        if (
            not policy
            or not service.env["mc.rov.automation.control"]._creation_enabled(alert.company_id)
            or not policy.enabled
            or not service._in_scope(alert)
        ):
            return False
        reason = policy._configuration_error(alert)
        if reason:
            alert.message_post(body=_("Seguimiento automático no generado: %s", reason))
            return False
        deadline = policy._deadline(started_at)
        activity = (
            service.env["mail.activity"]
            .sudo()
            .with_company(alert.company_id)
            .create(
                {
                    "res_model_id": service.env["ir.model"]._get_id("quality.alert"),
                    "res_id": alert.id,
                    "activity_type_id": service.env.ref(
                        "mc_rov.activity_type_quality_resolution"
                    ).id,
                    "summary": _("Resolver alerta de Calidad"),
                    "note": Markup('<p><a href="/odoo/quality.alert/%s">%s</a></p>')
                    % (alert.id, alert.display_name),
                    "user_id": policy.user_id.id,
                    "mc_employee_id": policy.employee_id.id or False,
                    "date_deadline": deadline,
                }
            )
        )
        return runs.create(
            {
                "company_id": alert.company_id.id,
                "alert_id": alert.id,
                "cycle": latest.cycle + 1 if latest else 1,
                "activity_id": activity.id,
                "started_at": started_at,
                "original_deadline": deadline,
                "current_deadline": deadline,
                "calendar_id": policy.calendar_id.id,
                "calendar_tz": policy.calendar_id.tz,
            }
        )
