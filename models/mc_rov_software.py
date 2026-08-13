from odoo import models, fields


class McRovSoftwareSuperficie(models.Model):
    """Catálogo del software de superficie que puede correr un ROV.

    Era un Selection hasta 19.0.9.0.0. Se convirtió en catálogo no por poder agregar
    valores —eso un Selection también lo permite, a costa de un despliegue— sino por poder
    **retirarlos**: sacar una opción de un Selection deja huérfanos los equipos que la
    tienen guardada y obliga a una migración de limpieza cada vez. Con `active` el registro
    histórico sigue resolviendo y la opción simplemente deja de ofrecerse.

    Eso importa porque el panorama ya está en movimiento: ROVControl es temporal y lo
    reemplaza Crabby.
    """

    _name = "mc.rov.software.superficie"
    _description = "Software de superficie ROV"
    _order = "sequence, name"

    name = fields.Char(string="Software", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)


class McRovControladorVuelo(models.Model):
    """Catálogo de controladores de vuelo.

    Mismo caso y misma razón que el software de superficie: Navigator reemplazó a Pixhawk y
    a su vez está previsto reemplazarlo. Retirar una opción tiene que ser desmarcar una
    casilla, no una migración.
    """

    _name = "mc.rov.controlador.vuelo"
    _description = "Controlador de vuelo ROV"
    _order = "sequence, name"

    name = fields.Char(string="Controlador", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
