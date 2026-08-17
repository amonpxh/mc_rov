from odoo import models, fields, api
from odoo.exceptions import UserError

# Una visita al taller genera UNA revisión, no dos. El par recepción/entrega venía de la
# idea de comparar el antes y el después dentro de la misma orden, pero la hoja de papel que
# esto reemplaza es una ficha por equipo reparado, y nadie llena dos fichas por visita. La
# comparación no se pierde: se hace contra la revisión de la visita ANTERIOR, que es además
# el intervalo que le interesa al análisis de fallas.
TIPOS = [
    ("fabricacion", "Fabricación"),
    ("reparacion", "Reparación"),
    ("terreno", "Prueba en terreno"),
]

# Qué campo del catálogo de chequeos habilita cada tipo de revision. Se lee de aquí en vez
# de encadenar ifs, para que agregar un tipo sea tocar dos listas y no buscar condicionales
# repartidos por el archivo.
CAMPO_APLICA = {
    "fabricacion": "aplica_fabricacion",
    "reparacion": "aplica_reparacion",
    "terreno": "aplica_terreno",
}

RESULTADOS_CHEQUEO = [
    ("ok", "OK"),
    ("no_ok", "No OK"),
    # "No aplica" afirma algo sobre el equipo: no lo tiene, o no corresponde revisarlo. No
    # se confunde con "no lo revisamos" porque eso no es un valor, es el campo vacío — y un
    # chequeo vacío impide confirmar la revisión. El denominador de las estadísticas queda
    # intacto y la palabra es la que usa el taller.
    ("no_lo_tiene", "No aplica"),
]

# El estado en que se encontró el sello de un componente. Es una sola dimensión y no tres
# casillas ("sello antiguo", "sello nuevo", "marca de plumón") porque el sello tiene
# continuidad: el que se pone hoy es el que se inspecciona en la próxima visita, y lo que
# interesa saber es en qué estado llegó.
#
# **El estado que se registra es siempre el de la llegada.** Antes eso lo garantizaba el
# tipo de la revisión —una de recepción se llenaba al recibir—; con una sola revisión por
# visita lo garantiza la etiqueta del campo y el aviso de la pestaña. Importa: el taller
# rompe sellos durante el trabajo, y anotar ese estado en vez del de llegada convierte
# trabajo propio en evidencia de manipulación de terceros.
#
# En fabricación no hay nada que inspeccionar: no existe sello previo ni visita anterior.
TIPOS_CON_INSPECCION = ("reparacion",)

ESTADOS_SELLO = [
    ("intacto", "Intacto"),
    ("roto", "Roto"),
    ("ausente", "Ausente"),
    ("sin_sello_previo", "Sin sello previo"),
    ("no_lo_tiene", "No aplica"),
]

SEVERIDADES = [
    ("informativo", "Informativo"),
    ("atencion", "Requiere atención"),
    ("impide_operar", "Impide operar"),
]


class McRovRevision(models.Model):
    """Una sesión de pruebas sobre un equipo: la ficha de reparación, digital.

    Reemplaza la hoja de papel del taller. Lo que esa hoja registra bien es **qué se
    probó**; lo que registra mal son los hallazgos, que caen todos en un campo de
    observaciones en texto libre y por eso no se pueden contar ni comparar.

    Cuelga del número de serie y no de la orden de reparación **a propósito**: un ROV nuevo
    pasa por la misma batería antes de despacharse y ahí no hay orden. Si colgara de la
    orden, toda la fabricación quedaría fuera del análisis.
    """

    _name = "mc.rov.revision"
    _description = "Revisión técnica ROV"
    _inherit = ["mail.thread"]
    _order = "fecha desc, id desc"
    _rec_name = "name"

    name = fields.Char(string="Revisión", readonly=True, copy=False, default="/")

    lot_id = fields.Many2one(
        "stock.lot",
        string="Número de serie",
        required=True,
        index=True,
        ondelete="cascade",
    )

    repair_id = fields.Many2one(
        "repair.order",
        string="Orden de reparación",
        index=True,
        ondelete="set null",
        help="La visita al taller, si la hubo. Vacío en las revisiones de fabricación, que "
        "ocurren antes de que exista ninguna orden.",
    )

    tipo = fields.Selection(TIPOS, string="Tipo", required=True, default="reparacion")

    fecha = fields.Date(string="Fecha", required=True, default=fields.Date.context_today)

    # hr.employee y no res.users porque los técnicos no tienen login propio —las licencias
    # se pagan por usuario— y porque son dos cosas distintas de todos modos: quién hizo el
    # trabajo físico y quién lo tecleó. No es required a nivel de modelo para que la vista
    # pueda exigirlo sin que un empleado ficticio ensucie la lista para siempre.
    responsable_id = fields.Many2one(
        "hr.employee",
        string="Responsable",
        default=lambda self: self.env.user.employee_id,
        help="Quién hizo el trabajo, que no siempre es quien llena la ficha.",
    )

    estado = fields.Selection(
        [("borrador", "Borrador"), ("confirmado", "Confirmado")],
        string="Estado",
        default="borrador",
        required=True,
        tracking=True,
        copy=False,
    )

    horas_operacion = fields.Float(
        string="Horómetro (h)",
        digits=(10, 1),
        help="Lectura del horómetro al recibir el equipo, si lo tiene. Lo que sirve para "
        "análisis es la diferencia entre dos revisiones: las horas que voló entre una "
        "visita y la siguiente.",
    )

    # --- Derivados: la revisión no guarda contactos propios ---

    product_id = fields.Many2one(related="lot_id.product_id", string="Modelo", readonly=True)
    es_un_rov = fields.Boolean(related="lot_id.es_un_rov", readonly=True)

    # De quién es el equipo (dura años) frente a quién paga esta visita (dura lo que dura la
    # orden). Guardar un tercer contacto acá reabriría la confusión que se cerró en 19.0.5.0.0.
    propietario_id = fields.Many2one(
        related="lot_id.mc_propietario_id", string="Propietario", readonly=True
    )
    partner_id = fields.Many2one(
        related="repair_id.partner_id", string="Cliente de la orden", readonly=True
    )

    # --- Mediciones que no dependen del umbilical ---

    luces_internas = fields.Integer(string="Luces internas")
    luces_externas = fields.Integer(string="Luces externas")

    luces_total = fields.Integer(string="Total luces", compute="_compute_luces", store=True)
    luces_ficha = fields.Integer(
        related="lot_id.mc_cantidad_luces", string="Luces según ficha", readonly=True
    )
    luces_difieren = fields.Boolean(
        string="El conteo no cuadra", compute="_compute_luces", store=True
    )

    # --- La corrida: con qué se probó ---
    #
    # Estos campos vivían en `mc.rov.revision.corrida`, un modelo de línea que permitía varias
    # corridas por revisión. Subieron acá en 19.0.15.0.0 y ese modelo desapareció.
    #
    # **La razón por la que estaban abajo resultó ser falsa a medias.** El argumento era que
    # "lo que no depende del cable vive en la revisión y se hace una sola vez aunque haya dos
    # corridas". Pero varios chequeos sí dependen del cable —responde a comandos, ancho de
    # banda, y probablemente video— y con dos corridas compartiendo un solo juego de
    # respuestas, **todo chequeo que cambiara entre cables se perdía en silencio**: la
    # comparación quedaba visible en cuatro números y en nada más.
    #
    # Ahora una revisión es una prueba completa bajo una condición: un cable, una batería, un
    # juego de respuestas. Comparar dos cables son dos revisiones, y cuesta responder los
    # chequeos de nuevo — que es exactamente lo que hace que la comparación sirva.
    #
    # No llevan `required` a nivel de modelo porque la revisión se crea sola al confirmar la
    # orden, antes de que nadie haya probado nada. Se exigen al confirmar.

    # «Del taller» se usa como muestra de control frente al cable del equipo, y también
    # **porque el ROV llegó sin el suyo** — raro, pero pasa. Una revisión con este valor puede
    # ser cualquiera de las dos cosas; lo que las distingue es `motivo`.
    umbilical = fields.Selection(
        [("equipo", "Del equipo"), ("prueba", "Del taller")],
        string="Umbilical",
        default="equipo",
        help="Con qué cable se corrió esta batería. «Del taller» puede ser una comparación "
        "de control o el único cable disponible, si el equipo llegó sin el suyo.",
    )
    largo = fields.Float(string="Largo del umbilical (m)")

    alimentacion = fields.Selection(
        [("UPS", "UPS"), ("Generador", "Generador"), ("Transformador", "Transformador")],
        string="Alimentación",
    )
    tension_salida = fields.Integer(string="Tensión de salida (V)")

    # El resultado del esfuerzo es binario —el ROV corre 1 a 1½ horas en un bin con agua y
    # o aguanta o presenta problemas— pero cuánto aguantó es información distinta y
    # comparable. "Aguantó 90 minutos" y "falló a los 15" quedarían registrados igual sin la
    # duración. Si falló, es tiempo hasta la falla; si pasó, es la fuerza de la evidencia.
    esfuerzo_duracion = fields.Float(string="Duración del esfuerzo (h)", digits=(5, 2))
    esfuerzo_resultado = fields.Selection(
        [("ok", "Sin problemas"), ("con_problemas", "Presentó problemas")],
        string="Resultado del esfuerzo",
    )

    # No hay campo "ancho de banda": ese es el nombre de la prueba, no una tercera medición.
    subida = fields.Float(string="Subida (Mbps)", digits=(6, 2))
    bajada = fields.Float(string="Bajada (Mbps)", digits=(6, 2))

    # Dato interno: se medía, se le entregaba al cliente y el cliente la usó en contra. Vuelve
    # a medirse con la condición de que NO salga en el reporte impreso.
    temperatura_interior = fields.Float(string="Temperatura interior (°C)")
    temperatura_exterior = fields.Float(string="Temperatura exterior (°C)")

    # Por qué existe esta revisión. Solo tiene sentido a partir de la segunda de una visita:
    # la primera es la primera y `numero_en_visita` ya lo dice.
    #
    # Sin este campo, dos revisiones en una misma visita son ambiguas —¿se arregló y se volvió
    # a probar, o se comparó un cable?— y mezclarlas corrompe el análisis que más importa:
    # «¿cuántas veces el segundo pase todavía muestra la falla?» no significa nada si la mitad
    # de esos segundos pases eran comparaciones de cable.
    #
    # Se podría inferir del umbilical —si difiere, es comparación— pero miente cuando un
    # re-test usa otro cable por casualidad. Lo contesta quien aprieta «Nueva revisión», que
    # sabe perfectamente por qué lo está apretando.
    motivo = fields.Selection(
        [
            ("primer_diagnostico", "Primer diagnóstico"),
            ("retest", "Re-test tras reparación"),
            ("comparacion_cable", "Comparación de cable"),
            ("otro", "Otro"),
        ],
        string="Motivo de esta revisión",
        default="primer_diagnostico",
        help="Por qué existe esta revisión. La primera de una visita diagnostica; las "
        "siguientes comprueban una reparación o comparan un cable, y contarlas juntas "
        "arruina la pregunta de si la reparación sirvió.",
    )

    # --- Solo en pruebas de terreno ---

    lugar = fields.Char(string="Lugar")
    profundidad = fields.Integer(string="Profundidad (m)")
    velocidad_corriente = fields.Float(string="Velocidad de la corriente (kn)")

    # --- Líneas ---

    chequeo_ids = fields.One2many("mc.rov.revision.chequeo", "revision_id", string="Chequeos")
    hallazgo_ids = fields.One2many("mc.rov.revision.hallazgo", "revision_id", string="Hallazgos")
    inspeccion_ids = fields.One2many(
        "mc.rov.revision.inspeccion", "revision_id", string="Inspección de sellos"
    )

    # Las mismas líneas de chequeo_ids, repartidas por sección. No hay columnas nuevas: los
    # siete campos comparten tabla e inverso y solo se diferencian por el dominio.
    #
    # Existen para que la pantalla se parezca a la hoja de papel, donde las pruebas vienen
    # en bloques con título —"Prueba de video", "Prueba de navegación"— y se llenan de
    # arriba abajo. La alternativa era una sola lista agrupada por sección, pero un grupo
    # hay que desplegarlo antes de escribir dentro, y un checklist que exige clics previos
    # es un checklist que se llena a medias.
    #
    # Se escribe solo `resultado` y `detalle` a través de estos campos: las líneas las crea
    # `_generar_chequeos` y las vistas van con create="0" delete="0", así que dos secciones
    # sucias en el mismo guardado solo emiten actualizaciones y nunca comandos en conflicto.
    chequeo_inspeccion_fisica_ids = fields.One2many(
        "mc.rov.revision.chequeo",
        "revision_id",
        domain=[("seccion", "=", "inspeccion_fisica")],
        string="Inspección física",
    )
    chequeo_energia_ids = fields.One2many(
        "mc.rov.revision.chequeo",
        "revision_id",
        domain=[("seccion", "=", "energia")],
        string="Prueba de energía",
    )
    chequeo_presion_ids = fields.One2many(
        "mc.rov.revision.chequeo",
        "revision_id",
        domain=[("seccion", "=", "presion")],
        string="Prueba de presión",
    )
    chequeo_leak_ids = fields.One2many(
        "mc.rov.revision.chequeo",
        "revision_id",
        domain=[("seccion", "=", "leak")],
        string="Prueba de leak",
    )
    chequeo_comunicacion_ids = fields.One2many(
        "mc.rov.revision.chequeo",
        "revision_id",
        domain=[("seccion", "=", "comunicacion")],
        string="Prueba de comunicación",
    )
    chequeo_navegacion_ids = fields.One2many(
        "mc.rov.revision.chequeo",
        "revision_id",
        domain=[("seccion", "=", "navegacion")],
        string="Prueba de navegación",
    )
    chequeo_video_ids = fields.One2many(
        "mc.rov.revision.chequeo",
        "revision_id",
        domain=[("seccion", "=", "video")],
        string="Prueba de video",
    )
    chequeo_luces_ids = fields.One2many(
        "mc.rov.revision.chequeo",
        "revision_id",
        domain=[("seccion", "=", "luces")],
        string="Prueba de luces",
    )
    chequeo_accesorios_ids = fields.One2many(
        "mc.rov.revision.chequeo",
        "revision_id",
        domain=[("seccion", "=", "accesorios")],
        string="Prueba de accesorios",
    )
    chequeo_otro_ids = fields.One2many(
        "mc.rov.revision.chequeo",
        "revision_id",
        domain=[("seccion", "=", "otro")],
        string="Otras pruebas",
    )

    # Varias revisiones en una misma visita son legítimas —se prueba, se arregla, se
    # vuelve a probar— pero envenenan las estadísticas si no se sabe cuál es cuál: la tasa
    # de "equipos que llegan con el motor roto" cae a un tercio si una visita tuvo tres
    # revisiones y el hallazgo está en una.
    #
    # La regla es que la unidad de análisis es la VISITA, no la revisión. Este número la
    # hace inequívoca: la #1 dice con qué llegó el equipo, la última cómo quedó. Sin él
    # habría que ordenar por fecha, y varias del mismo día no se ordenan solas.
    numero_en_visita = fields.Integer(
        string="N° en la visita",
        compute="_compute_numero_en_visita",
        store=True,
        help="1 para la primera revisión de esta orden, 2 para la siguiente, etc. Las "
        "revisiones sin orden asociada quedan en 0.",
    )

    @api.depends("repair_id", "fecha")
    def _compute_numero_en_visita(self):
        for revision in self:
            if not revision.repair_id:
                revision.numero_en_visita = 0
                continue
            hermanas = self.search([("repair_id", "=", revision.repair_id.id)], order="fecha, id")
            revision.numero_en_visita = (
                list(hermanas).index(revision) + 1 if revision in hermanas else 1
            )

    resultado = fields.Selection(
        [
            ("aprobado", "Aprobado"),
            ("aprobado_con_observaciones", "Aprobado con observaciones"),
            ("rechazado", "Rechazado"),
        ],
        string="Resultado",
        compute="_compute_resultado",
        store=True,
        help="Se deriva de los chequeos, el esfuerzo y los hallazgos. No es editable: un "
        "override sería el texto libre de vuelta, en otra forma.",
    )

    @api.depends("luces_internas", "luces_externas", "luces_ficha")
    def _compute_luces(self):
        """El conteo de la prueba contra la especificación del equipo.

        Si el ROV debería tener seis luces y se contaron cuatro, el sistema lo dice sin que
        nadie tenga que acordarse de comparar. Es una de las cosas que la inspección busca.
        """
        for revision in self:
            revision.luces_total = revision.luces_internas + revision.luces_externas
            revision.luces_difieren = bool(revision.luces_ficha) and (
                revision.luces_total != revision.luces_ficha
            )

    @api.depends(
        "chequeo_ids.resultado",
        "esfuerzo_resultado",
        "hallazgo_ids.severidad",
    )
    def _compute_resultado(self):
        """El orden de las condiciones es la regla de negocio.

        Un chequeo fallado o un esfuerzo con problemas rechazan la revisión aunque no se
        haya registrado ningún hallazgo: el equipo no pasó, y eso no se compensa con que
        nadie haya escrito por qué.

        **Y una revisión a medio llenar no dice nada: queda vacía.** Hasta 19.0.15.1.0 caía
        en «Aprobado» por descarte, así que una ficha recién creada —con los 22 chequeos sin
        responder y nada probado— declaraba que el equipo estaba bien. Es el vacío
        indistinguible de un dato, y encima del lado optimista.
        """
        for revision in self:
            sin_responder = any(not linea.resultado for linea in revision.chequeo_ids)
            if sin_responder or not revision.esfuerzo_resultado:
                revision.resultado = False
                continue

            rechaza = (
                any(linea.resultado == "no_ok" for linea in revision.chequeo_ids)
                or revision.esfuerzo_resultado == "con_problemas"
                or any(hallazgo.severidad == "impide_operar" for hallazgo in revision.hallazgo_ids)
            )
            if rechaza:
                revision.resultado = "rechazado"
            elif revision.hallazgo_ids:
                revision.resultado = "aprobado_con_observaciones"
            else:
                revision.resultado = "aprobado"

    # --- Generación del checklist ---

    def _chequeos_del_tipo(self, tipo):
        """Los chequeos activos del catálogo que corresponden a este tipo de revision."""
        campo = CAMPO_APLICA.get(tipo)
        if not campo:
            return self.env["mc.rov.chequeo"]
        return self.env["mc.rov.chequeo"].search([(campo, "=", True)])

    def _generar_chequeos(self, revision):
        """Crea las líneas de checklist que falten para el tipo de la revisión.

        Las genera el sistema y no la persona porque el punto de un checklist es que
        siempre traiga los mismos ítems: si el técnico eligiera cuáles agregar, no habría
        forma de distinguir "revisado y limpio" de "no se me ocurrió mirarlo".

        Solo agrega lo que falta y nunca borra respuestas. Un chequeo respondido sobrevive
        aunque cambie el tipo de la revisión, porque el dato ya se levantó y perderlo sería
        peor que tener una línea de más.

        Recibe la revisión como argumento en vez de operar sobre self: lo llaman create y
        write sobre un registro a la vez, siguiendo la convención del módulo.
        """
        Linea = self.env["mc.rov.revision.chequeo"]
        # Solo los marcados como inspeccionables: sin ese filtro un chequeo "por componente"
        # generaría una línea por cada entrada del catálogo, incluidos umbilical, cámara o
        # sensor, que no se revisan buscando sellos de terceros.
        componentes = self.env["mc.rov.componente"].search([("es_inspeccionable", "=", True)])
        existentes = {
            (linea.chequeo_id.id, linea.componente_id.id) for linea in revision.chequeo_ids
        }

        valores = []
        for chequeo in self._chequeos_del_tipo(revision.tipo):
            objetivos = componentes if chequeo.por_componente else [False]
            for componente in objetivos:
                componente_id = componente.id if componente else False
                if (chequeo.id, componente_id) in existentes:
                    continue
                valores.append(
                    {
                        "revision_id": revision.id,
                        "chequeo_id": chequeo.id,
                        "componente_id": componente_id,
                        "sequence": chequeo.sequence,
                    }
                )

        if valores:
            Linea.create(valores)

    def _generar_inspeccion(self, revision):
        """Crea una fila por componente sellado, si el tipo de revision la lleva.

        Igual que el checklist, la genera el sistema: si el técnico eligiera qué
        componentes revisar, la ausencia de una fila no distinguiría "no lo tiene" de
        "no lo miré".
        """
        if revision.tipo not in TIPOS_CON_INSPECCION:
            return

        componentes = self.env["mc.rov.componente"].search([("es_inspeccionable", "=", True)])
        existentes = revision.inspeccion_ids.mapped("componente_id")

        valores = [
            {"revision_id": revision.id, "componente_id": componente.id}
            for componente in componentes - existentes
        ]
        if valores:
            self.env["mc.rov.revision.inspeccion"].create(valores)

    def _limpiar_chequeos_sin_responder(self, revision):
        """Borra las líneas que dejaron de corresponder y que nadie contestó.

        Solo las sin responder: cambiar el tipo de una revisión a medio llenar no debe
        borrar trabajo hecho.
        """
        validos = self._chequeos_del_tipo(revision.tipo)
        sobrantes = revision.chequeo_ids.filtered(
            lambda linea: not linea.resultado and linea.chequeo_id not in validos
        )
        sobrantes.unlink()

    def action_actualizar_checklist(self):
        """Trae los pasos que se agregaron al catálogo después de que nació esta ficha.

        Las líneas se copian del catálogo cuando la revisión se crea, y la revisión se crea
        al confirmar la orden — o sea, apenas el equipo entra al taller. El efecto es que un
        chequeo agregado al catálogo un martes no le llega a ninguno de los equipos que ya
        están en el taller, solo a los que entren después, y quien lo agregó no tiene forma
        de darse cuenta.

        No se actualiza solo, a propósito: una ficha a medio llenar que cambia de contenido
        sin que nadie la toque es peor que una desactualizada, porque el técnico ya la
        recorrió y no la vuelve a leer entera. Que lo pida una persona fija el momento.

        Solo agrega — `_generar_chequeos` nunca borra respuestas — así que apretarlo de más
        no cuesta nada. Queda en el chatter porque explica por qué la ficha creció entre
        que se abrió y que se llenó.
        """
        self.ensure_one()
        if self.estado != "borrador":
            raise UserError(
                "Una revisión confirmada ya no cambia de checklist. Vuélvala a borrador "
                "si de verdad falta un paso."
            )

        antes = len(self.chequeo_ids) + len(self.inspeccion_ids)
        self._generar_chequeos(self)
        self._generar_inspeccion(self)
        nuevas = len(self.chequeo_ids) + len(self.inspeccion_ids) - antes

        if nuevas:
            self.message_post(
                body=f"Se agregaron {nuevas} líneas nuevas desde el catálogo de chequeos."
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("mc.rov.revision") or "/"

        revisiones = super().create(vals_list)
        for revision in revisiones:
            self._generar_chequeos(revision)
            self._generar_inspeccion(revision)
        return revisiones

    def write(self, vals):
        res = super().write(vals)
        if "tipo" in vals:
            for revision in self:
                self._limpiar_chequeos_sin_responder(revision)
                self._generar_chequeos(revision)
                self._generar_inspeccion(revision)
        return res

    # --- Confirmación ---

    def _faltantes_para_confirmar(self, revision):
        """Qué le impide a esta revisión pasar a confirmado, en lenguaje del taller.

        Se devuelve una lista y no el primer problema encontrado: hacer que el técnico
        descubra los faltantes de a uno, guardando entre medio, es la forma más segura de
        que abandone.
        """
        faltan = []

        if not revision.responsable_id:
            faltan.append("indicar el responsable")

        # La prueba de esfuerzo siempre se hace, incluso cuando la revisión existe solo para
        # comparar un cable: el taller confirmó que nunca se cambia el umbilical solo para
        # medir ancho de banda.
        if not revision.esfuerzo_resultado:
            faltan.append("el resultado de la prueba de esfuerzo")
        if revision.esfuerzo_resultado and not revision.esfuerzo_duracion:
            faltan.append("cuánto duró el esfuerzo")
        if not revision.alimentacion:
            faltan.append("la alimentación usada")
        if not revision.largo:
            faltan.append("el largo del umbilical con el que se probó")
        if bool(revision.subida) != bool(revision.bajada):
            faltan.append("la subida y la bajada — o ambas, o ninguna")

        # Por qué existe la revisión. La primera de una visita trae "primer diagnóstico" por
        # defecto; la que abre el botón nace vacía a propósito, para forzar la elección justo
        # donde importa. Sin esto, un re-test tras reparación y una comparación de cable se
        # ven idénticos, y contarlos juntos arruina la pregunta de si la reparación sirvió.
        #
        # Solo se pide cuando hay visita: en una revisión de fabricación no hay a qué
        # compararla ni reparación que comprobar.
        if revision.repair_id and not revision.motivo:
            faltan.append("por qué se abrió esta revisión")

        sin_responder = revision.chequeo_ids.filtered(lambda linea: not linea.resultado)
        if sin_responder:
            faltan.append(f"responder {len(sin_responder)} chequeo(s) pendiente(s)")

        sellos_sin_ver = revision.inspeccion_ids.filtered(lambda linea: not linea.estado_sello)
        if sellos_sin_ver:
            faltan.append(f"revisar el sello de {len(sellos_sin_ver)} componente(s)")

        return faltan

    def action_confirmar(self):
        """Cierra la revisión. A partir de aquí el registro es evidencia, no borrador."""
        for revision in self:
            faltan = self._faltantes_para_confirmar(revision)
            if faltan:
                detalle = "\n".join(f"· {item}" for item in faltan)
                raise UserError(
                    f"Falta lo siguiente para confirmar {revision.display_name}:\n\n{detalle}"
                )
            revision.estado = "confirmado"

    def action_volver_a_borrador(self):
        """Reabre una revisión confirmado. Existe porque las fichas se equivocan.

        Queda en el chatter, que es lo que distingue una corrección de un borrado.
        """
        for revision in self:
            revision.estado = "borrador"
            revision.message_post(body="La revisión volvió a borrador para corregirse.")


class McRovRevisionChequeo(models.Model):
    """Una línea del checklist: qué se revisó y qué salió.

    El campo `resultado` cubre dos dimensiones con un solo valor, porque la ficha de papel
    registra principalmente *qué se testeó* y no *qué resultó*. Vacío significa que todavía
    no se responde —y eso impide confirmar—, mientras que «No aplica» es una respuesta
    válida y de uso corriente.
    """

    _name = "mc.rov.revision.chequeo"
    _description = "Línea de chequeo de una revisión"
    _order = "revision_id, sequence, id"

    revision_id = fields.Many2one(
        "mc.rov.revision", string="Revisión", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(default=10)

    chequeo_id = fields.Many2one(
        "mc.rov.chequeo", string="Chequeo", required=True, ondelete="restrict"
    )
    seccion = fields.Selection(related="chequeo_id.seccion", string="Sección", store=True)

    componente_id = fields.Many2one("mc.rov.componente", string="Componente", ondelete="restrict")

    resultado = fields.Selection(RESULTADOS_CHEQUEO, string="Resultado")
    detalle = fields.Char(string="Detalle")

    @api.model
    def _search_display_name(self, operator, value):
        """Deja escribir para filtrar, que sin esto no funciona en absoluto.

        Odoo busca por `_rec_name`, y este modelo no tiene ninguno: sin este override,
        escribir en el desplegable de «Prueba que lo detectó» no matchea nada y la única
        salida es abrir «Buscar más» y elegir de una lista de veinte filas. Mostrar bien el
        nombre no alcanzaba — hay que poder buscarlo.

        El componente entra en la búsqueda solo con operadores positivos: en un `not ilike`
        el OR devolvería de más, porque bastaría que una de las dos partes no coincidiera.
        """
        dominio = [("chequeo_id.name", operator, value)]
        if operator in ("=", "like", "ilike", "=like", "=ilike"):
            return ["|"] + dominio + [("componente_id.name", operator, value)]
        return dominio

    @api.depends("chequeo_id.name", "componente_id.name")
    def _compute_display_name(self):
        """Nombra la línea por el chequeo que representa.

        El modelo no tiene `name` ni `_rec_name`, así que sin esto Odoo devuelve
        "mc.rov.revision.chequeo,50" — y ese es el texto que salía en el desplegable de
        «Detectado por» al registrar un hallazgo, o sea justo donde hay que elegir cuál
        prueba lo destapó. Un identificador técnico ahí no permite elegir nada.

        El componente entra cuando la línea es una de las que se generan por componente: sin
        él, cinco filas del mismo chequeo se leerían idénticas.
        """
        for linea in self:
            etiqueta = linea.chequeo_id.name or "Chequeo"
            if linea.componente_id:
                etiqueta = f"{etiqueta} · {linea.componente_id.name}"
            linea.display_name = etiqueta


class McRovRevisionHallazgo(models.Model):
    """Lo que se encontró, estructurado.

    Reusa `mc.rov.componente` y `mc.rov.subtipo`, los mismos catálogos que usan las líneas
    de trabajo. Eso es lo que permite correlacionar: *dónde* se encuentran los hallazgos y
    *dónde* se hacen los trabajos hablan el mismo idioma.

    `detalle` sigue existiendo pero como complemento del hallazgo, nunca en su lugar. Sin la
    parte estructurada el técnico escribe "se vio raro el motor" y no hay nada que agregar.
    """

    _name = "mc.rov.revision.hallazgo"
    _description = "Hallazgo registrado en una revisión"
    _order = "revision_id, sequence, id"

    revision_id = fields.Many2one(
        "mc.rov.revision", string="Revisión", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(default=10)

    componente_id = fields.Many2one(
        "mc.rov.componente", string="Componente", required=True, ondelete="restrict"
    )
    subtipo_id = fields.Many2one(
        "mc.rov.subtipo",
        string="Subtipo",
        domain="[('componente_id', '=', componente_id)]",
        ondelete="restrict",
    )
    hallazgo_id = fields.Many2one(
        "mc.rov.hallazgo", string="Hallazgo", required=True, ondelete="restrict"
    )
    severidad = fields.Selection(
        SEVERIDADES, string="Severidad", required=True, default="atencion"
    )

    # El eje de detección del FMEA, y el que casi ningún taller puede calcular: si el
    # hallazgo lo reveló un chequeo de la revisión o si alguien lo vio de casualidad. De ahí
    # sale el resultado más útil de todos — un hallazgo frecuente que ningún chequeo detecta
    # es un chequeo que falta.
    # "Detectado por" se leía como si preguntara por la persona. La etiqueta tiene que nombrar
    # la respuesta que se espera, que es una prueba del checklist.
    chequeo_origen_id = fields.Many2one(
        "mc.rov.revision.chequeo",
        string="Prueba que lo detectó",
        ondelete="set null",
        help="Cuál de las pruebas de esta revisión destapó el hallazgo. Déjelo vacío si se "
        "encontró por fuera del checklist, mirando el equipo.\n\n"
        "De acá sale la pregunta más útil que estos datos permiten: un hallazgo que aparece "
        "seguido y que ninguna prueba detecta es un chequeo que falta en la batería.\n\n"
        "La inspección de sellos no entra acá y no hace falta que entre: ya registra su "
        "propio resultado en cada fila. Lo que un sello dice es si alguien más abrió el "
        "equipo, no qué está fallando.",
    )

    detalle = fields.Text(string="Detalle")

    lot_id = fields.Many2one(related="revision_id.lot_id", string="Equipo", store=True)

    @api.model
    def _search_display_name(self, operator, value):
        """Mismo caso que la línea de chequeo: sin esto no se puede buscar escribiendo.

        Acá pesa más todavía, porque el desplegable de «Resuelve el hallazgo» lista los
        hallazgos de todo el equipo y no los de una revisión: la lista es larga desde la
        segunda visita.
        """
        dominio = [("hallazgo_id.name", operator, value)]
        if operator in ("=", "like", "ilike", "=like", "=ilike"):
            return ["|"] + dominio + [("componente_id.name", operator, value)]
        return dominio

    @api.depends("componente_id.name", "subtipo_id.name", "hallazgo_id.name")
    def _compute_display_name(self):
        """Nombra el hallazgo por dónde y qué, que es como lo busca quien lo enlaza.

        Mismo caso que la línea de chequeo: sin esto Odoo devuelve
        "mc.rov.revision.hallazgo,12", y ese era el texto del desplegable «Resuelve el
        hallazgo» en la pestaña Reparación — el campo que cierra el circuito entre lo que se
        encontró y lo que se arregló. Con un identificador técnico ahí, nadie lo enlaza, y sin
        el enlace la línea de trabajo queda con «por qué pasó» y sin «qué se encontró».
        """
        for hallazgo in self:
            donde = hallazgo.componente_id.name or "Sin componente"
            if hallazgo.subtipo_id:
                donde = f"{donde} / {hallazgo.subtipo_id.name}"
            hallazgo.display_name = f"{donde} · {hallazgo.hallazgo_id.name or 'sin hallazgo'}"


class McRovRevisionInspeccion(models.Model):
    """El estado del sello de un componente en una visita.

    Reemplaza a tres casillas independientes —"sello antiguo", "sello nuevo", "marca de
    plumón"— que no podían expresar el proceso real. El sello tiene **continuidad**: el que
    se pone hoy es el que se inspecciona en la próxima visita, y si llega roto eso es la
    evidencia de que alguien más abrió el equipo.

    Un solo campo alcanza porque el tipo de la revisión da el contexto: en recepción el
    estado es *cómo llegó*, en entrega es *cómo se dejó*. Y no hace falta distinguir quién
    rompió el sello, porque el taller nunca lo rompe sin registrarlo y sus roturas ocurren
    durante el trabajo, después de la recepción.
    """

    _name = "mc.rov.revision.inspeccion"
    _description = "Inspección de sellos de una revisión"
    _order = "revision_id, componente_id"

    revision_id = fields.Many2one(
        "mc.rov.revision", string="Revisión", required=True, ondelete="cascade", index=True
    )
    componente_id = fields.Many2one(
        "mc.rov.componente", string="Componente", required=True, ondelete="restrict"
    )

    # "al recibir" en el nombre y no solo en la ayuda: es la única cosa que impide que el
    # técnico anote aquí un sello que él mismo rompió al abrir el equipo.
    estado_sello = fields.Selection(ESTADOS_SELLO, string="Estado del sello al recibir")
    observacion = fields.Char(string="Observación")

    tipo = fields.Selection(related="revision_id.tipo", store=True)
    lot_id = fields.Many2one(related="revision_id.lot_id", string="Equipo", store=True)

    # Almacenado para poder contar manipulaciones sin recorrer revisiones en cada consulta.
    # Solo en las revisiones de reparación: en fabricación no hay sello previo que romper.
    manipulacion_externa = fields.Boolean(
        string="Evidencia de manipulación",
        compute="_compute_manipulacion_externa",
        store=True,
        help="Se enciende cuando el equipo llegó al taller con el sello roto o ausente.",
    )

    @api.depends("estado_sello", "tipo")
    def _compute_manipulacion_externa(self):
        for linea in self:
            linea.manipulacion_externa = linea.tipo == "reparacion" and linea.estado_sello in (
                "roto",
                "ausente",
            )
