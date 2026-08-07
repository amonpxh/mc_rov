from odoo import models, api

# Campos de sale_stock_renting que mueven un equipo dentro o fuera de un arriendo.
CAMPOS_ARRIENDO = ("pickedup_lot_ids", "returned_lot_ids")


class SaleOrderLine(models.Model):
    """Extensión de sale.order.line para mantener sincronizado stock.lot.mc_estado_comercial.

    "En arriendo" se decide comparando los lotes retirados contra los devueltos de la
    línea, pero desde stock.lot no existe relación que traversar hasta acá, así que
    @api.depends no puede verlo. Este override hace el papel que en el caso de es_un_rov
    hace product.category: avisarle al ORM qué recalcular.

    Sin esto el equipo saldría de arriendo y su número de serie seguiría diciendo
    "Disponible" hasta que alguien tocara otro campo — el mismo desajuste silencioso que
    el módulo viene eliminando.
    """

    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        """Cubre las líneas que nacen con equipos ya retirados, como en una importación."""
        lines = super().create(vals_list)
        self._recalcular_estado_comercial(self._lotes_de_arriendo(lines))
        return lines

    def write(self, vals):
        """Recalcula el estado de los equipos que entran o salen de la línea.

        Se juntan los lotes de antes y los de después: quitar un equipo de la lista de
        retirados también cambia su estado, y después del super() ya no aparece.
        """
        toca_arriendo = any(campo in vals for campo in CAMPOS_ARRIENDO)
        antes = self._lotes_de_arriendo(self) if toca_arriendo else self.env["stock.lot"]

        res = super().write(vals)

        if toca_arriendo:
            self._recalcular_estado_comercial(antes | self._lotes_de_arriendo(self))

        return res

    def _lotes_de_arriendo(self, lines):
        """Equipos mencionados por `lines`, retirados o devueltos.

        Recibe las líneas como argumento en vez de operar sobre self porque create las
        llama sobre un recordset recién creado, y llamar métodos protegidos de otro
        recordset es lo que pylint marca como protected-access. Mismo criterio que
        _ultima_fecha_entrega en stock_lot.py.
        """
        return lines.mapped("pickedup_lot_ids") | lines.mapped("returned_lot_ids")

    def _recalcular_estado_comercial(self, lots):
        rovs = lots.filtered("es_un_rov")
        if rovs:
            self.env.add_to_compute(rovs._fields["mc_estado_comercial"], rovs)
