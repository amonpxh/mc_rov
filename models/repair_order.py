from odoo import api, models, fields
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    """Extensión de repair.order para gestión de ROVs.

    Agrega campos específicos del flujo de reparación de Marine Connection:
    tipo de intervención, ítems adicionales del sistema, registro de la falla
    reportada por el cliente, detalle de trabajos realizados y resultado final.
    """

    _inherit = "repair.order"

    # Clasifica la intervención para efectos de reportes y estadísticas.
    # Es Many2many y no Selection porque una misma visita al taller puede ser varias
    # cosas: el equipo entra a mantención y de paso se le repara algo. La relación se
    # nombra explícitamente para que la migración 19.0.4.0.0 pueda escribir en ella.
    tipo_intervencion_ids = fields.Many2many(
        "mc.rov.tipo.intervencion",
        relation="mc_rov_repair_order_tipo_rel",
        column1="repair_order_id",
        column2="tipo_id",
        string="Tipo de intervención",
    )

    # Reemplaza a los cuatro item_2..item_5 heredados de Studio: Char sin etiqueta, con la
    # cantidad fija en el código, y que ninguna de las diez órdenes de producción usó nunca.
    # Un Many2many no tiene tope y es trazable — los e-pods llevan número de serie propio,
    # así que queda registrado cuál llegó con cuál ROV en cuál visita.
    mc_items_recibidos_ids = fields.Many2many(
        "stock.lot",
        relation="mc_rov_repair_order_item_rel",
        column1="repair_order_id",
        column2="lot_id",
        string="Equipos recibidos",
        # Sin dominio se podía meter otro ROV como si fuera un accesorio, y ese equipo
        # quedaba sin revisión, sin chequeos y sin historial: invisible para todo el
        # análisis. El dominio también excluye al propio equipo de la orden, que es un ROV.
        domain="[('es_un_rov', '=', False)]",
        help="Lo que llegó junto al ROV: consola, umbilical, e-pods. Es lo que la "
        "inspección física de la revisión va a mirar. No acepta otros ROV: cada vehículo "
        "necesita su propia orden para tener revisión e historial.",
    )

    # Descripción literal de la falla según el cliente, sin interpretación técnica
    falla_reportada = fields.Text(string="Falla reportada por cliente")

    # --- Recepción: lo que alguien dice, separado de lo que el taller comprueba ---
    #
    # Los dos viven en la orden y no en la revisión porque se llenan en una ventana que no
    # vuelve: la recepción es la única vez que hay alguien a quien preguntarle. El cliente se
    # va y no vuelve, y para cuando el equipo está abierto ya nadie contesta.
    #
    # Ninguno es obligatorio, a propósito: un síntoma vacío es honestamente vacío —el que
    # trajo el equipo puede no haberlo operado nunca— y obligar produciría inventos. Lo que
    # cubre el hueco es el filtro "Sin síntoma registrado" de la vista de búsqueda.

    # Lo que el cliente VIO. El criterio para distinguirlo de la sospecha es "¿lo vio, o lo
    # deduce?": "un motor no gira" es síntoma, "creo que es el umbilical" es sospecha.
    sintoma_ids = fields.Many2many(
        "mc.rov.sintoma",
        relation="mc_rov_repair_order_sintoma_rel",
        column1="repair_order_id",
        column2="sintoma_id",
        string="Síntomas",
        help="Lo que el cliente vio, no lo que deduce. Si se cortó el umbilical y el corte "
        "está a la vista, es un síntoma; si solo lo sospecha, va en el campo de al lado.",
    )

    # Lo que el cliente DEDUCE. Reusa el catálogo de componentes —el mismo de los hallazgos y
    # los trabajos— para que "sospechó del umbilical, resultó ser el conector" sea una
    # consulta y no una lectura de párrafos. Un catálogo propio obligaría a mantener una
    # tabla de equivalencias que nadie mantendría.
    componente_sospechado_ids = fields.Many2many(
        "mc.rov.componente",
        relation="mc_rov_repair_order_sospecha_rel",
        column1="repair_order_id",
        column2="componente_id",
        string="El cliente sospecha de",
        help="De qué componente sospecha el cliente, aunque no lo haya visto. Que quede "
        "vacío también es dato: significa que el equipo llegó sin diagnóstico.",
    )

    # Las revisiones de esta visita. Normalmente una sola —la que se abre sola al confirmar
    # la orden—; una segunda aparece cuando el equipo se prueba, se arregla y se vuelve a
    # probar, y ahí `numero_en_visita` es lo que distingue con qué llegó de cómo quedó.
    revision_ids = fields.One2many(
        "mc.rov.revision",
        "repair_id",
        string="Revisiones técnicas",
    )

    # Almacenado porque es criterio de un filtro de la lista de órdenes, y un campo sin store
    # no se puede filtrar. Se enciende cuando la visita tiene alguna revisión a medio llenar.
    #
    # Es una señal y no un bloqueo, a propósito. Exigir la revisión confirmada para cerrar la
    # orden obligaría a recorrer los veinte chequeos aunque el equipo haya entrado a cambiar
    # un conector — y cuando responder cuesta, se marca "No aplica" en cadena para pasar el
    # trámite, que envenena el dato mucho más que una revisión en borrador. Además el vacío
    # acá no es ambiguo: el estado dice "Borrador", que es exactamente lo que pasa.
    mc_revision_pendiente = fields.Boolean(
        string="Revisión sin confirmar",
        compute="_compute_mc_revision_pendiente",
        store=True,
        help="Se enciende cuando alguna revisión técnica de esta visita quedó en borrador.",
    )

    @api.depends("revision_ids.estado")
    def _compute_mc_revision_pendiente(self):
        for order in self:
            order.mc_revision_pendiente = any(
                revision.estado == "borrador" for revision in order.revision_ids
            )

    def action_nueva_revision(self):
        """Crea una revisión de esta visita y la abre para llenarla.

        Existe para el segundo pase: la primera revisión la abre sola `_crear_revision` al
        confirmar la orden. Sin este botón, volver a probar un equipo después de arreglarlo
        obligaría a salir al menú, buscar el número de serie y volver — una navegación que
        nadie iba a hacer, y el resultado sería que la segunda prueba no queda registrada.
        """
        self.ensure_one()
        revision = self.env["mc.rov.revision"].create(
            {
                "lot_id": self.lot_id.id,
                "repair_id": self.id,
                "tipo": "reparacion",
                # Sin motivo a propósito: la primera revisión de la visita trae "primer
                # diagnóstico" por defecto, y esta nace vacía para que quien la abre diga por
                # qué. Es la única que puede ser un re-test o una comparación de cable, y
                # confundirlas arruina la pregunta de si la reparación sirvió.
                "motivo": False,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Revisión técnica",
            "res_model": "mc.rov.revision",
            "res_id": revision.id,
            "view_mode": "form",
            "target": "current",
        }

    # Detalle técnico de los trabajos ejecutados (ver mc.rov.linea.falla)
    linea_falla_ids = fields.One2many(
        "mc.rov.linea.falla", "repair_id", string="Trabajos realizados"
    )

    # Las mismas líneas, mostradas en la pestaña Resultado para contestar origen y "por qué
    # pasó". No hay columnas nuevas: comparten tabla e inverso y solo se diferencian por la
    # vista. Es el mismo patrón que los siete campos chequeo_*_ids de la revisión.
    #
    # El momento ya lo garantiza la validación del cierre; lo que arregla este campo es la
    # PANTALLA. "Trabajos realizados" es donde se anota mientras se trabaja y su lista ya
    # lleva diez columnas: un campo de texto como columna doce es donde el texto se muere.
    # La pestaña Resultado es la de cierre —ahí ya están la fecha de entrega y las
    # observaciones de salida— y es donde el origen se puede afirmar.
    #
    # Su vista va con create="0" delete="0": de la pantalla de cierre no se crean ni se
    # borran trabajos, así que las dos listas sucias en el mismo guardado solo emiten
    # actualizaciones y nunca comandos en conflicto.
    linea_falla_cierre_ids = fields.One2many(
        "mc.rov.linea.falla", "repair_id", string="Por qué pasó"
    )
    # Almacenado porque es columna de la lista de órdenes: sin store la columna se ve
    # pero no se puede ordenar, filtrar ni agrupar, que es justo lo que se le pide a un
    # total de horas. La columna es nueva, así que el ORM la calcula sola al crearla y
    # no hace falta migración.
    mc_total_horas = fields.Float(
        string="Total HH.",
        compute="_compute_mc_total_horas",
        store=True,
        digits=(5, 1),
    )

    @api.depends("linea_falla_ids.horas")
    def _compute_mc_total_horas(self):
        for order in self:
            order.mc_total_horas = sum(order.linea_falla_ids.mapped("horas"))

    fecha_entrega_real = fields.Date(
        string="Fecha de entrega real",
        help="Se completa sola con la fecha de cierre si queda vacía. Corríjala si la "
        "entrega al cliente ocurrió otro día.",
    )
    observaciones_salida = fields.Text(string="Observaciones de salida")

    # --- Propiedad del equipo ---

    mc_propietario_lot_id = fields.Many2one(
        "res.partner",
        string="Propietario registrado",
        related="lot_id.mc_propietario_id",
        readonly=True,
    )

    mc_propietario_difiere = fields.Boolean(
        string="El propietario no coincide",
        compute="_compute_mc_propietario_difiere",
        help="Se enciende cuando el cliente de la orden no es el propietario que tiene "
        "registrado el equipo. Casi siempre significa que el ROV se revendió.",
    )

    @api.depends("lot_id", "partner_id", "mc_propietario_lot_id")
    def _compute_mc_propietario_difiere(self):
        """Solo compara cuando hay las dos puntas y el equipo es un ROV.

        En los lotes de componentes el propietario es siempre la empresa y la
        comparación daría alerta en todas las órdenes.
        """
        for order in self:
            order.mc_propietario_difiere = bool(
                order.lot_id.es_un_rov
                and order.partner_id
                and order.mc_propietario_lot_id
                and order.partner_id != order.mc_propietario_lot_id
            )

    @api.onchange("lot_id")
    def _onchange_lot_id_propone_propietario(self):
        """Propone como cliente al propietario registrado del equipo.

        Propuesta y no imposición: quien paga la orden no siempre es el dueño. Puede ser
        un seguro, un distribuidor que trae el equipo de un tercero, o el comprador de un
        ROV de segunda mano. Por eso solo rellena el campo vacío y nunca pisa lo que el
        técnico ya eligió.
        """
        for order in self:
            propietario = order.lot_id.mc_propietario_id
            if propietario and order.lot_id.es_un_rov and not order.partner_id:
                order.partner_id = propietario

    def action_actualizar_propietario_lote(self):
        """Traspasa el equipo al cliente de esta orden.

        Es la vía por la que el sistema se entera de que un ROV se revendió: nadie nos
        avisa de la venta entre terceros, pero el equipo vuelve al taller a nombre de
        otro. El contexto deja esta orden anotada en el historial como el origen del
        traspaso.

        No devuelve acción a propósito: al recargarse el formulario desaparece el aviso,
        que es la confirmación de que el cambio quedó hecho.
        """
        self.ensure_one()
        self.lot_id.with_context(mc_rov_repair_origen=self.id).write(
            {"mc_propietario_id": self.partner_id.id}
        )

    def _validar_tipo_intervencion(self):
        """Impide cerrar una orden que no dice qué tipo de trabajo fue.

        Sin tipo, la orden es invisible para todo lo que se calcula a partir de ella: no
        cuenta como mantención ni como reparación, no reinicia el ciclo del equipo, no
        suma a los contadores y no aparece en ultima_mantencion ni ultima_reparacion. Y
        nada avisa — es la misma falla silenciosa que tenía fecha_entrega_real, con el
        mismo síntoma diferido: meses después el equipo sigue apareciendo vencido.
        """
        sin_tipo = self.filtered(lambda order: not order.tipo_intervencion_ids)
        if not sin_tipo:
            return

        # display_name y no name: name puede venir vacío y romper el join.
        nombres = ", ".join(sin_tipo.mapped("display_name"))
        raise UserError(
            f"Indique el tipo de intervención antes de cerrar: {nombres}.\n\n"
            "Sin tipo, el trabajo no cuenta como mantención ni como reparación: no "
            "reinicia el ciclo de mantención del equipo ni aparece en su historial."
        )

    def _validar_origen(self):
        """Impide cerrar una orden con trabajos de los que no se dijo por qué pasaron.

        Va acá y no como `required` en el campo, y la diferencia importa: un `required`
        exigiría el origen al guardar cada línea, o sea mientras el técnico todavía está
        reparando y la respuesta es especulación. El resultado sería «No determinado» marcado
        para salir del paso, que es indistinguible de un «no determinado» de verdad. Al
        cerrar ya se sabe, y se contestan todas juntas.

        Es además el campo que decide quién paga —si el origen es diseño o manufactura la
        reparación la paga la empresa; si es uso del cliente, la paga el cliente— así que
        bloquear el cierre no agrega una traba, formaliza una que ya existía.

        **Una orden sin líneas de trabajo se cierra sin problema.** Una visita de diagnóstico
        puro no registra trabajos, y eso no la deja incompleta.
        """
        sin_origen = self.linea_falla_ids.filtered(lambda linea: not linea.origen)
        if not sin_origen:
            return

        detalle = "\n".join(f"· {linea.display_name}" for linea in sin_origen)
        raise UserError(
            f"Indique el origen de estos trabajos antes de cerrar:\n\n{detalle}\n\n"
            "Es lo que decide si la reparación la paga la empresa o el cliente. Si no se "
            "pudo establecer, «No determinado» es una respuesta válida y deja cerrar."
        )

    def _validar_repuestos(self):
        """Impide cerrar una orden que cambió una pieza y no registró ninguna.

        Una línea de trabajo con acción «Cambio completo» y cero líneas de producto significa
        que se cambió algo y no quedó anotado. El costo no es administrativo: se pierde el
        vínculo con el lote de la pieza, y con él la mitad del análisis de fallas por
        componente — no se puede saber qué repuesto falla más ni cuánto dura.

        Qué acciones lo exigen sale de la casilla `consume_repuesto` del catálogo, nunca de
        comparar nombres: mañana aparece "Reemplazo de sello" y tiene que poder marcarse sin
        desplegar código.

        **Pide al menos un repuesto, no uno por cada cambio.** Una orden con tres cambios y
        una sola pieza registrada pasa. Es un piso deliberado: la correspondencia uno a uno
        exigiría decir qué repuesto va con qué trabajo, y ese es un campo que hoy no existe.
        """
        for order in self:
            exigen = order.linea_falla_ids.filtered(lambda linea: linea.accion_id.consume_repuesto)
            if not exigen or order.move_ids:
                continue

            detalle = "\n".join(f"· {linea.display_name}" for linea in exigen)
            raise UserError(
                f"Estos trabajos cambian una pieza y no hay ningún repuesto registrado en "
                f"{order.display_name}:\n\n{detalle}\n\n"
                "Agregue el repuesto en la pestaña Repuestos. Sin él se pierde el vínculo "
                "con el número de serie de la pieza, y no se puede saber después qué "
                "componente falla más seguido."
            )

    def _crear_revision(self, order):
        """Abre la revisión técnica de una orden que acaba de entrar al taller.

        Se crea sola y no con un botón porque **siempre ocurre**: toda visita se registra
        en una ficha. Depender de que alguien se acuerde de apretar algo es lo que hace que
        un paso obligatorio se salte en silencio, y meses después nadie entienda por qué no
        hay datos.

        Es el criterio inverso al de la revisión de fabricación, que sí es un botón: esa a
        veces ocurre y a veces no.

        Tres condiciones, y las tres importan:

        - **Al salir de borrador**, no al crearse. Una orden en borrador es una cotización
          y el equipo puede no haber llegado todavía; es la misma distinción que usan
          mc_estado_operativo y los contadores.
        - **Solo ROVs.** Una reparación de componente no lleva revisión.
        - **Solo si no hay una.** Un ida y vuelta entre estados no debe generar duplicados.
          Solo cubre la primera: una segunda revisión se pide a mano con el botón, y esa es
          precisamente la que no debe crearse sola.
        """
        if not order.lot_id or not order.lot_id.es_un_rov:
            return

        Revision = self.env["mc.rov.revision"]
        if Revision.search_count([("repair_id", "=", order.id), ("tipo", "=", "reparacion")]):
            return

        Revision.create({"lot_id": order.lot_id.id, "repair_id": order.id, "tipo": "reparacion"})
        order.message_post(body="Se abrió la revisión técnica de esta visita.")

    def write(self, vals):
        """Abre la revisión técnica, valida el cierre y sella la fecha de entrega.

        La validación va **antes** del super() para que el estado no llegue a
        escribirse. Y cubre solo la transición a done, no un @api.constrains, para no
        bloquear la edición de órdenes anteriores a la regla.

        El sellado va después, y por la razón contraria: no debe pisar una fecha que
        venga en el mismo vals.

        ultima_mantencion y ultima_reparacion en stock.lot dependen de esa fecha. Que
        quedara vacía significaba que el trabajo no contaba y el ciclo del equipo no se
        reiniciaba, sin ninguna advertencia: el técnico cerraba la orden y el número de
        serie seguía apareciendo vencido para siempre.

        Solo cubre write y no create: una orden nacida ya cerrada viene de una
        importación de datos históricos, y ahí estamparle la fecha de hoy inventaría un
        dato peor que dejarlo vacío. Quien importe debe traer su propia fecha.
        """
        if vals.get("state") == "done":
            self._validar_tipo_intervencion()
            self._validar_origen()
            self._validar_repuestos()

        # Se anota antes del super() quiénes estaban en borrador: después ya cambiaron.
        entran_al_taller = (
            self.filtered(lambda order: order.state == "draft")
            if vals.get("state") not in (None, "draft", "cancel")
            else self.browse()
        )

        res = super().write(vals)

        for order in entran_al_taller:
            self._crear_revision(order)

        if vals.get("state") == "done":
            sin_fecha = self.filtered(lambda order: not order.fecha_entrega_real)
            if sin_fecha:
                sin_fecha.fecha_entrega_real = fields.Date.context_today(self)

        return res
