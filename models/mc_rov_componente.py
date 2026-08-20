from markupsafe import escape

from odoo import api, models, fields
from odoo.exceptions import UserError

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

    # Guardar la alerta y no solo crearla: sin este campo el botón duplica en cada clic, y
    # además la línea no muestra que la lección ya se levantó. Es la traza que cierra el
    # circuito reparación → fabricación, del mismo modo que `hallazgo_origen_id` cierra el
    # de revisión → trabajo.
    mc_alerta_id = fields.Many2one(
        "quality.alert",
        string="Alerta de calidad",
        ondelete="set null",
        readonly=True,
        help="La lección de fabricación levantada desde este trabajo.",
    )

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

    def action_crear_alerta_calidad(self):
        """Levanta la alerta de calidad de este trabajo, pre-llenada desde el origen.

        Es el canal por el que un patrón de fabricación descubierto tarde vuelve a
        fabricación (§ 6.3 del diseño). Reparación ve lo que fabricación no puede ver
        —toda la flota, y años de exposición— así que una línea con origen «diseño» o
        «manufactura propia» es una lección de manufactura ya escrita, que hasta ahora no
        tenía destinatario.

        El botón está acá y no en la app de Calidad por la regla que ordena toda la guía
        del usuario: **el siguiente paso tiene que ser un botón en el registro que ya
        estás mirando.** Quien repara nunca tiene que enterarse de que Calidad existe.
        """
        self.ensure_one()
        if not self.repair_id:
            raise UserError("Esta línea no cuelga de ninguna orden de reparación.")

        # Idempotente: el segundo clic abre la alerta que ya existe en vez de duplicarla.
        # Sin esto, una línea larga de trabajo termina con tres alertas del mismo problema
        # y el conteo por modelo —que es lo que dice cuándo un diseño maduró (§ 6.4)—
        # empieza a mentir hacia arriba.
        alerta = self.mc_alerta_id.exists()
        if not alerta:
            alerta = self.env["quality.alert"].create(self._mc_valores_de_alerta())
            self.mc_alerta_id = alerta

        return {
            "name": "Alerta de calidad",
            "type": "ir.actions.act_window",
            "res_model": "quality.alert",
            "views": [(self.env.ref("quality_control.quality_alert_view_form").id, "form")],
            "res_id": alerta.id,
        }

    def _mc_valores_de_alerta(self):
        """Lo que la línea puede afirmar sobre el problema, puesto donde la alerta lo espera.

        `title` queda vacío, igual que en la alerta que nace de un chequeo fallido: la
        alerta tiene que verse a medio llenar para que alguien la termine.

        La causa raíz se resuelve por XML ID y no por nombre. **Ése es el contrato con el
        bloque D**, que alinea el catálogo `quality.reason` con `ORIGENES` creando
        `mc_rov.quality_reason_<origen>`. Mientras D no exista, esto devuelve vacío y la
        persona elige la razón a mano; cuando exista, el botón empieza a llenarla sin
        tocar una línea de este archivo.
        """
        self.ensure_one()
        equipo = self.repair_id.product_id
        razon = (
            self.env.ref(f"mc_rov.quality_reason_{self.origen}", raise_if_not_found=False)
            if self.origen
            else None
        )
        return {
            "product_id": equipo.id,
            "product_tmpl_id": equipo.product_tmpl_id.id,
            # El equipo reparado es la unidad afectada conocida. Si el problema resulta
            # ser del modelo, quien escriba la lección agrega las demás.
            "lot_ids": self.repair_id.lot_id.ids,
            "repair_id": self.repair_id.id,
            "reason_id": razon.id if razon else False,
            "description": self._mc_descripcion_de_alerta(),
        }

    def _mc_descripcion_de_alerta(self):
        """El razonamiento de la línea, copiado a la alerta en vez de referenciado.

        `analisis_causa` responde «por qué pasó», que es exactamente lo que la lección
        necesita y lo que se pierde si la alerta solo enlaza a la orden: seis meses
        después nadie abre la reparación para leerlo.
        """
        self.ensure_one()
        etiquetas = dict(self._fields["origen"].selection)
        lineas = [
            f"Origen: {etiquetas.get(self.origen, 'sin determinar')}",
            f"Trabajo: {self.display_name}",
        ]
        if self.analisis_causa:
            lineas.append(self.analisis_causa)
        if self.detalle:
            lineas.append(self.detalle)
        return "".join(f"<p>{escape(linea)}</p>" for linea in lineas)
