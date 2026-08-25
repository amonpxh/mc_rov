from odoo import models, fields


class QualityReason(models.Model):
    """Las causas de calidad, que Odoo entrega sin poder retirarse.

    **`quality.reason` no trae `active`**, verificado en el ensayo de `19.0.23.0.0` sobre una
    copia de producción: la migración que iba a archivar las cuatro de fábrica encontró que
    la columna no existía y se detuvo sin tocar nada.

    Sin ese campo, una entrada del catálogo solo se puede **borrar**, y borrar es la respuesta
    equivocada dos veces: si una alerta vieja la usaba, se lleva el dato; y si el módulo de
    Odoo se vuelve a actualizar, la recrea. Archivar la retira del desplegable, conserva lo
    ya escrito, y se deshace desde la pantalla.

    Es lo que este módulo ya necesitaba de todos modos para su propia decisión —retirar las
    cuatro de Odoo, que pisan a tres de las nuestras— y lo que hace cierta la frase de que
    **el catálogo es del usuario**: un catálogo del que no se puede sacar nada no lo es.
    """

    _inherit = "quality.reason"

    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Desmarque para retirar esta causa del desplegable sin perder las alertas que "
        "ya la usan.",
    )
