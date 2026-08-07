from odoo import models, fields


class McRovPropietarioHistorial(models.Model):
    """Períodos de propiedad de un equipo ROV.

    Una fila por período, no por cambio: guarda desde cuándo y hasta cuándo un contacto
    fue dueño de la unidad. El período abierto (sin fecha_hasta) es el vigente y coincide
    siempre con mc_propietario_id del número de serie.

    Nadie mantiene esta tabla a mano — la escribe el override de write de stock.lot cada
    vez que cambia el propietario. Existe para análisis: cuánto tiempo estuvo cada unidad
    con cada cliente, por cuántas manos pasó, y si los equipos revendidos vuelven más
    seguido al taller. El partner_id de las órdenes de reparación no sirve para eso: a
    veces paga un seguro o un distribuidor en vez del dueño, y la venta original nunca
    genera una orden de reparación.
    """

    _name = "mc.rov.propietario.historial"
    _description = "Período de propiedad de un ROV"
    _order = "fecha_desde desc, id desc"
    _rec_name = "partner_id"

    lot_id = fields.Many2one(
        "stock.lot",
        string="Número de serie",
        required=True,
        ondelete="cascade",
        index=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Propietario",
        required=True,
        index=True,
    )

    fecha_desde = fields.Date(
        string="Desde",
        required=True,
        help="Cuándo pasó a ser de este propietario. En los equipos que ya existían "
        "antes de esta funcionalidad es la fecha de creación del número de serie.",
    )

    fecha_hasta = fields.Date(
        string="Hasta",
        help="Vacío significa que es el propietario actual.",
    )

    # Cuando la reventa se descubre porque el equipo llegó al taller a nombre de otro,
    # queda registrado con qué orden se detectó. Vacío = el cambio se hizo a mano.
    repair_id = fields.Many2one(
        "repair.order",
        string="Detectado en",
        ondelete="set null",
        help="Orden de reparación en la que se detectó el cambio de propietario.",
    )
