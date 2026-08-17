from odoo import models, fields

# Secciones de la ficha de pruebas. Es un Selection y no un catálogo a propósito: las
# secciones son la estructura del documento y son estables, mientras que los chequeos que
# viven dentro de ellas son operativos y cambian. Un catálogo de secciones sería un
# catálogo de catálogos para resolver un problema que no existe.
#
# `energia` y `comunicacion` entran en 19.0.14.1.0. Salieron de contar la batería contra el
# catálogo de síntomas: un ROV que no enciende o que pierde conexión con la superficie no
# tenía ninguna prueba que lo verificara, así que el técnico lo iba a encontrar mirando y el
# hallazgo quedaría sin chequeo de origen. Se agregan como secciones y no como entradas de
# "Otro" porque son áreas de trabajo distintas —el arranque se verifica antes que nada, los
# comandos desde la consola— y un "Otro" que junta arranque, comandos y ancho de banda deja
# de decir qué se está probando.
SECCIONES = [
    ("inspeccion_fisica", "Inspección física"),
    ("energia", "Prueba de energía"),
    ("presion", "Prueba de presión"),
    ("leak", "Prueba de leak"),
    ("comunicacion", "Prueba de comunicación"),
    ("navegacion", "Prueba de navegación"),
    ("video", "Prueba de video"),
    # `accesorios` entra en 19.0.14.2.0. Manipulador y sonar los lleva una minoría de los
    # equipos, y eso no es razón para no preguntarlos: "No aplica" es una respuesta válida y
    # afirma algo del equipo. Sin la sección, un accesorio que no responde es un síntoma que
    # el cliente reporta y que la batería nunca verifica.
    ("accesorios", "Prueba de accesorios"),
    # Luces va última porque es la única sección que además pide números —el conteo de
    # internas y externas— y por lo tanto la única con una forma distinta. Al final, esa
    # forma no interrumpe el ritmo de las otras ocho, que son todas la misma lista.
    ("luces", "Prueba de luces"),
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

    # Cuando está encendido, la revisión genera una línea por componente inspeccionable
    # —E-pod, cilindro fuente, motores, consola, joystick— en vez de una sola respuesta
    # global. Desde 19.0.12.0.0 ningún chequeo del catálogo lo usa: el único que lo hacía
    # eran las marcas de plumón, que salieron de la batería. El mecanismo se conserva
    # porque la pregunta "esto hay que responderlo componente por componente" vuelve sola
    # cada vez que se agrega algo a la inspección física.
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
    #
    # `aplica_reparacion` reemplaza en 19.0.12.0.0 al par recepción/entrega, que dejó de
    # existir cuando la visita pasó a llevar una sola revisión.
    aplica_fabricacion = fields.Boolean(string="En fabricación")
    aplica_reparacion = fields.Boolean(string="En reparación", default=True)
    aplica_terreno = fields.Boolean(string="En terreno")

    active = fields.Boolean(default=True)
