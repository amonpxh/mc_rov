from odoo import models, fields

# Secciones de la ficha de pruebas. Es un Selection y no un catálogo a propósito: las
# secciones son la estructura del documento y son estables, mientras que los chequeos que
# viven dentro de ellas son operativos y cambian. Un catálogo de secciones sería un
# catálogo de catálogos para resolver un problema que no existe.
SECCIONES = [
    ("inspeccion_fisica", "Inspección física"),
    ("presion", "Prueba de presión"),
    ("leak", "Prueba de leak"),
    ("navegacion", "Prueba de navegación"),
    ("video", "Prueba de video"),
    ("otro", "Otro"),
]


class McRovChequeo(models.Model):
    """Catálogo de pasos de testeo estándar de una revisión técnica.

    Es la lista de qué se revisa siempre. Existe como catálogo y no como campos fijos
    porque la batería crece: un ROV de seis grados de libertad necesita chequeos de
    movimiento que uno de cuatro no tiene, y agregar sonar o USBL es marcar registros
    desde Reparaciones > Configuración en vez de desplegar código.
    """

    _name = "mc.rov.chequeo"
    _description = "Paso de testeo estándar ROV"
    _order = "seccion, sequence, name"

    name = fields.Char(string="Chequeo", required=True)
    sequence = fields.Integer(default=10)
    seccion = fields.Selection(SECCIONES, string="Sección", required=True, default="otro")

    # Cuando está encendido, la línea de la revisión debe decir sobre qué componente se hizo
    # el chequeo. Es lo que convierte "marcas de plumón" en cinco filas —una por E-pod,
    # cilindro fuente, motores, consola y joystick— en vez de una sola respuesta global.
    por_componente = fields.Boolean(
        string="Por componente",
        help="Marque los chequeos que se hacen componente por componente. La revisión "
        "generará una línea por cada componente inspeccionable.",
    )

    # Fabricación y reparación no corren la misma batería. El caso que lo justifica es la
    # inspección física: existe para detectar si alguien más intervino el equipo, y en un
    # ROV recién fabricado eso no significa nada. Sin este filtro, la revisión de
    # fabricación generaría quince líneas que alguien tendría que responder para poder
    # confirmar y que no dirían nada.
    aplica_fabricacion = fields.Boolean(string="En fabricación")
    aplica_recepcion = fields.Boolean(string="En recepción", default=True)
    aplica_entrega = fields.Boolean(string="En entrega")
    aplica_terreno = fields.Boolean(string="En terreno")

    active = fields.Boolean(default=True)
