from odoo import models, fields

FAMILIAS = [
    ("terceros", "Intervención de terceros"),
    ("estanqueidad", "Estanqueidad"),
    ("estructura", "Estructura"),
    ("electrico", "Eléctrico"),
    ("funcional", "Funcional"),
    ("otro", "Otro"),
]


class McRovHallazgo(models.Model):
    """Catálogo de lo que se puede encontrar en un equipo.

    Es la pieza que faltaba y la razón de todo el módulo de protocolos. `mc.rov.accion`
    registra **lo que se hizo**; hasta ahora no existía vocabulario para **lo que se
    encontró**, así que los hallazgos terminaban en un campo de texto libre y el análisis
    de patrones exigía leer los párrafos uno por uno.

    Es catálogo y no Selection porque tiene que crecer sin desplegar: cuando el técnico no
    encuentra el hallazgo que necesita, la respuesta correcta es agregarlo aquí desde
    Reparaciones > Configuración, no describirlo en prosa. Esa es la diferencia entre un
    catálogo vivo y uno decorativo.
    """

    _name = "mc.rov.hallazgo"
    _description = "Hallazgo en un equipo ROV"
    _order = "familia, sequence, name"

    name = fields.Char(string="Hallazgo", required=True)
    sequence = fields.Integer(default=10)
    familia = fields.Selection(FAMILIAS, string="Familia", required=True, default="otro")
    active = fields.Boolean(default=True)
