from odoo import _, models
from odoo.exceptions import AccessError


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
