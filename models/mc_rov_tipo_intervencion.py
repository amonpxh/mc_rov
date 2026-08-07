from odoo import models, fields


class McRovTipoIntervencion(models.Model):
    """Catálogo de tipos de intervención de una orden de reparación.

    Reemplaza al Selection tipo_intervencion, que obligaba a elegir un solo tipo por
    orden. Un ROV que entra a mantención y de paso necesita una reparación es una sola
    visita al taller con dos trabajos: forzar la elección hacía perder uno de los dos, y
    con él el reinicio del ciclo de mantención del equipo.

    Se gestiona desde Reparaciones > Configuración, igual que componentes y acciones.
    """

    _name = "mc.rov.tipo.intervencion"
    _description = "Tipo de intervención ROV"
    _order = "sequence, name"

    name = fields.Char(string="Tipo", required=True)
    sequence = fields.Integer(default=10)

    # El ciclo de mantención se calcula leyendo esta casilla, no comparando nombres:
    # si mañana agregan "Mantención mayor", la marcan aquí y el reloj la reconoce sin
    # que nadie toque el código.
    es_mantencion = fields.Boolean(
        string="Cuenta como mantención",
        help="Marque los tipos que reinician el ciclo de mantención del equipo. "
        "Una orden que incluya alguno de ellos actualiza la fecha de última mantención "
        "del número de serie.",
    )

    # Las dos casillas son independientes a propósito: una visita puede ser ambas cosas,
    # y un diagnóstico o una conversión no son ninguna de las dos.
    es_reparacion = fields.Boolean(
        string="Cuenta como reparación",
        help="Marque los tipos que constituyen una reparación del equipo. "
        "Una orden que incluya alguno de ellos actualiza la fecha de última reparación "
        "del número de serie y suma al contador de reparaciones.",
    )

    active = fields.Boolean(default=True)
