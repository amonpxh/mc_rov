from odoo import models


class ProductCategory(models.Model):
    """Extensión de product.category para mantener sincronizado stock.lot.es_un_rov.

    El campo es_un_rov depende de product_id.categ_id, lo que cubre que un producto
    cambie de categoría. No cubre el caso inverso: que la categoría cambie de padre y
    entre o salga de la rama ROV sin que ningún producto se mueva.
    """

    _inherit = "product.category"

    def write(self, vals):
        """Recalcula es_un_rov cuando una categoría cambia de padre.

        El recálculo va después del super() a propósito: recién ahí parent_path está
        actualizado y child_of devuelve los descendientes correctos, sirva la rama para
        entrar a ROV o para salir.
        """
        res = super().write(vals)

        if "parent_id" in vals:
            lots = self.env["stock.lot"].search([("product_id.categ_id", "child_of", self.ids)])
            if lots:
                self.env.add_to_compute(lots._fields["es_un_rov"], lots)

        return res
