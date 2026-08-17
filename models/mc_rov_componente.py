from odoo import api, models, fields

# De quién es el problema. Reemplaza a `causa_raiz` en 19.0.13.0.0, que mezclaba esta
# pregunta con la de qué le pasó físicamente al equipo — y esa ya la contesta el hallazgo:
# "Corrosión" y "Accidente", dos de los seis valores viejos, no eran causas raíz, y
# "Corrosión" existe literalmente como entrada del catálogo de hallazgos.
#
# Los paréntesis van en la etiqueta y no en el help: el campo es una columna de lista, así
# que el valor elegido se corta, pero el desplegable abierto muestra las opciones completas
# —que es justo cuando hace falta la aclaración—.
#
# Se nombra al responsable cuando hay uno. "Uso del cliente" y no "mal uso" porque este es el
# campo que decide quién paga la reparación, y un veredicto en la etiqueta sesga la respuesta.
ORIGENES = [
    ("diseno", "Diseño o especificación (lo pensamos mal)"),
    ("falla_fabricacion", "Manufactura propia (lo hicimos mal)"),
    ("pieza_proveedor", "Pieza de proveedor (vino fallada)"),
    ("mal_uso", "Uso del cliente (mal uso o accidente)"),
    ("desgaste", "Desgaste normal (duró lo que tenía que durar)"),
    ("desconocida", "No determinado"),
]


class McRovComponente(models.Model):
    """Catálogo maestro de componentes ROV.

    Agrupa los componentes físicos y de software que pueden fallar o
    intervenirse en una orden de reparación (motor, umbilical, cámara, etc.).
    Cada componente puede tener uno o varios subtipos para mayor precisión
    en el registro de trabajos realizados.
    """

    _name = "mc.rov.componente"
    _description = "Componente ROV"
    _order = "name"

    name = fields.Char(string="Componente", required=True)
    # Subtipos gestionados desde el formulario del componente (inline)
    subtipo_ids = fields.One2many("mc.rov.subtipo", "componente_id", string="Subtipos")

    # Qué componentes recorre la inspección física de la revisión. Es una casilla y no una
    # lista fija en el código para que agregar uno sea marcarlo desde Configuración, igual
    # que es_mantencion en los tipos de intervención. Sin esta marca, un chequeo "por
    # componente" generaría una línea por cada componente del catálogo —incluidos umbilical,
    # cámara o sensor, que no se inspeccionan buscando sellos ajenos.
    es_inspeccionable = fields.Boolean(
        string="Entra en la inspección física",
        help="Marque los componentes que se revisan uno por uno al recibir un equipo, "
        "buscando marcas de plumón o sellos de terceros.",
    )

    active = fields.Boolean(default=True)


class McRovSubtipo(models.Model):
    """Subtipo de un componente ROV.

    Permite detallar qué parte específica del componente fue intervenida.
    Por ejemplo, dentro de 'Motor' puede ser 'Rotor', 'Hélice' o 'ESC'.
    El dominio en mc.rov.linea.falla filtra los subtipos según el componente
    seleccionado en cada línea.
    """

    _name = "mc.rov.subtipo"
    _description = "Subtipo de componente ROV"
    _order = "componente_id, name"

    name = fields.Char(string="Subtipo", required=True)
    componente_id = fields.Many2one(
        "mc.rov.componente",
        string="Componente",
        required=True,
        ondelete="cascade",
    )
    active = fields.Boolean(default=True)


class McRovAccion(models.Model):
    """Catálogo de acciones realizadas en intervenciones ROV.

    Lista configurable de acciones estándar que el técnico puede seleccionar
    al registrar cada línea de trabajo (reparación, limpieza, calibración, etc.).
    Se gestiona desde Reparaciones > Configuración, igual que los componentes.
    """

    _name = "mc.rov.accion"
    _description = "Acción en intervención ROV"
    _order = "name"

    name = fields.Char(string="Acción", required=True)

    # Marca las acciones que necesariamente consumen una pieza del inventario. El cierre de la
    # orden lo valida: un "Cambio completo" sin ninguna línea de producto significa que se
    # cambió algo y no quedó registrado, y ahí se pierde el vínculo con el lote y se corta el
    # análisis de fallas por componente.
    #
    # Es una casilla del catálogo y no una lista de nombres en el código, por lo mismo que
    # `es_mantencion` en los tipos de intervención: mañana aparece "Reemplazo de sello" y
    # tienen que poder marcarla sin desplegar.
    consume_repuesto = fields.Boolean(
        string="Consume repuesto",
        help="Marque las acciones que siempre gastan una pieza del inventario. La orden no "
        "se podrá cerrar si hay un trabajo con esta acción y ningún repuesto registrado.",
    )

    active = fields.Boolean(default=True)


class McRovLineaFalla(models.Model):
    """Línea de trabajo registrada en una orden de reparación.

    Cada línea describe una intervención específica: qué componente se trató,
    qué subtipo exacto, qué acción se tomó, la fecha, las horas invertidas y
    un detalle libre. Una orden puede tener múltiples líneas.
    """

    _name = "mc.rov.linea.falla"
    _description = "Línea de falla en orden de reparación"
    # El id desempata: todas las líneas nacen en sequence = 10 y solo se separan si
    # alguien las arrastra. Sin el desempate, el orden entre ellas lo decide PostgreSQL
    # y las filas se rebarajan solas entre una lectura y la siguiente.
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    repair_id = fields.Many2one(
        "repair.order",
        string="Orden de reparación",
        required=True,
        ondelete="cascade",
    )
    componente_id = fields.Many2one("mc.rov.componente", string="Componente", required=True)
    # El dominio se evalúa por fila en el one2many editable (soportado desde Odoo 17+)
    subtipo_id = fields.Many2one(
        "mc.rov.subtipo",
        string="Subtipo",
        domain="[('componente_id', '=', componente_id)]",
    )
    accion_id = fields.Many2one(
        "mc.rov.accion",
        string="Acción",
        required=True,
        ondelete="restrict",
    )

    # Lo que cierra el circuito: qué hallazgo de la revisión de recepción resuelve este
    # trabajo. Con él se puede preguntar cuántos de los hallazgos de entrada quedaron
    # cerrados, y qué hallazgo predice qué acción. Opcional porque un trabajo puede surgir
    # sin hallazgo previo, y un hallazgo puede quedarse sin resolver — que también es dato.
    hallazgo_origen_id = fields.Many2one(
        "mc.rov.revision.hallazgo",
        string="Resuelve el hallazgo",
        ondelete="set null",
    )

    # En la línea y no solo en la cabecera: dos técnicos pueden trabajar la misma orden y
    # cada línea ya lleva sus horas. Sin esto las HH no se pueden atribuir, y agregarlo
    # después dejaría sin atribuir todo lo anterior.
    responsable_id = fields.Many2one(
        "hr.employee",
        string="Responsable",
        help="Quién hizo este trabajo en particular.",
    )

    # No lleva `required`: eso lo exigiría al guardar la línea, o sea mientras el técnico
    # todavía está reparando y el origen es especulación. Se exige al CERRAR la orden
    # (`repair.order._validar_origen`), que es el único momento en que se puede afirmar.
    # Mismo criterio que `responsable_id` de la revisión.
    origen = fields.Selection(
        ORIGENES,
        string="Origen",
        help="Diseño o especificación: se armó tal como estaba definido y aun así falló. "
        "Incluye elegir la pieza equivocada (un conector IP67 donde hacía falta IP68) y no "
        "haber previsto las condiciones donde el equipo iba a trabajar.\n"
        "Manufactura propia: estaba bien definido y el trabajo salió malo — soldadura, "
        "sellado, torque, cableado.\n"
        "Pieza de proveedor: la pieza comprada vino defectuosa de fábrica.\n"
        "Uso del cliente: se operó fuera de lo indicado, o hubo un accidente.\n"
        "Desgaste normal: cumplió su vida útil.\n"
        "No determinado: no se pudo establecer. Es una respuesta válida.\n\n"
        "Esto sirve para mejorar el producto, no para buscar culpables. «Manufactura "
        "propia» y «Diseño» son respuestas normales y esperables.",
    )

    # El razonamiento que justifica el origen elegido. Entre el hallazgo ("O-ring dañado") y
    # el origen ("diseño") hay un salto que ningún campo guardaba, y sin él un conteo alto de
    # "diseño" no se puede revisar seis meses después.
    #
    # Texto y no un modelo de porqués numerados: la cantidad de eslabones varía —a veces son
    # tres, a veces ocho— y obligar a cinco produce relleno. Además se retira barato si
    # resulta que solo se llena en los casos complejos, que es lo que se espera.
    #
    # Nunca obligatorio, y en particular tampoco cuando el origen apunta hacia adentro:
    # ponerle fricción justo a las opciones incómodas empuja a marcar "desgaste normal", que
    # es plausible siempre.
    analisis_causa = fields.Text(
        string="Por qué pasó",
        help="El razonamiento que lleva al origen elegido. Escriba lo que haga falta: dos "
        "frases si el caso es evidente, o la cadena completa de porqués si no lo es.",
    )
    # Por defecto hoy: la línea se registra el día en que se hace el trabajo, y sin
    # default quedaba vacía casi siempre. Una fecha corregible sirve más que un campo en
    # blanco, porque de ella depende poder situar cada trabajo en el tiempo.
    fecha = fields.Date(string="Fecha", default=fields.Date.context_today)
    horas = fields.Float(string="HH.", digits=(5, 1))
    detalle = fields.Text(string="Detalle")

    @api.depends("componente_id", "subtipo_id", "accion_id")
    def _compute_display_name(self):
        """Nombra la línea por lo que se hizo y dónde.

        Sin esto el modelo no tiene `name` ni `_rec_name`, así que Odoo devuelve
        "mc.rov.linea.falla,42" — y ese es el texto que vería el técnico en el error que le
        impide cerrar la orden por falta de origen. Mismo caso y misma solución que
        `mc.rov.revision.chequeo` y `mc.rov.revision.hallazgo`.
        """
        for linea in self:
            componente = linea.componente_id.name or "sin componente"
            if linea.subtipo_id:
                componente = f"{componente} / {linea.subtipo_id.name}"
            accion = linea.accion_id.name or "sin acción"
            linea.display_name = f"{componente} · {accion}"
