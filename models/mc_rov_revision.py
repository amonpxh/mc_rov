from odoo import models, fields, api
from odoo.exceptions import UserError

# Una visita al taller genera UNA revisión, no dos. El par recepción/entrega venía de la
# idea de comparar el antes y el después dentro de la misma orden, pero la hoja de papel que
# esto reemplaza es una ficha por equipo reparado, y nadie llena dos fichas por visita. La
# comparación no se pierde: se hace contra la revisión de la visita ANTERIOR, que es además
# el intervalo que le interesa al análisis de fallas.
# `fabricacion` se retiró en 19.0.16.0.0. Era genérico y nunca tuvo justificación escrita,
# y además había dejado de describir una sola cosa: lo que pasa mientras se arma son puntos
# de calidad, y lo que pasa después es esta prueba.
#
# Se llama `rendimiento` y no `rendimiento` porque tiene que contrastar con `terreno` en el mismo
# eje —dónde se prueba— o el desplegable deja abierta la pregunta «¿y la de terreno no mide
# rendimiento?». La etiqueta nunca dice «Banco» a secas por la misma razón.
TIPOS = [
    ("rendimiento", "Prueba de rendimiento"),
    ("reparacion", "Reparación"),
    ("terreno", "Prueba en terreno"),
]

# Qué campo del catálogo de chequeos habilita cada tipo de revision. Se lee de aquí en vez
# de encadenar ifs, para que agregar un tipo sea tocar dos listas y no buscar condicionales
# repartidos por el archivo.
CAMPO_APLICA = {
    "rendimiento": "aplica_rendimiento",
    "reparacion": "aplica_reparacion",
    "terreno": "aplica_terreno",
}

# Dónde el funcionamiento continuo —la corrida de resistencia— es parte de la batería.
#
# En terreno no lo es, y el criterio no es la relevancia sino la física: no hay dónde dejar
# un equipo andando hora y media colgado de un bote. Sin esta lista, `_compute_resultado`
# exigía su resultado siempre, así que **una revisión de terreno no podía quedar aprobada
# nunca** — se quedaba en blanco para siempre, que es el mismo modo de falla que
# `19.0.15.1.0` vino a arreglar del otro lado. Ver `designs/fabricacion.md` § 4.7.
TODOS_LOS_TIPOS = ("rendimiento", "terreno", "reparacion")

TIPOS_CON_FUNCIONAMIENTO_CONTINUO = {"rendimiento", "reparacion"}

# Las dos pruebas que son parte del nacimiento del equipo y no de su vida posterior (§ 4.2).
TIPOS_DE_ACEPTACION = ("rendimiento", "terreno")

# Lo que la ficha declaraba CUANDO SE CORRIÓ LA PRUEBA, campo de la revisión → campo del lote.
#
# **Se congelan al confirmar, y ésa es toda la razón de que existan como campos propios.**
# Antes eran `related` en vivo, así que una revisión de hace seis meses mostraba la ficha de
# hoy — y peor: `luces_difieren` se recalculaba, o sea que un documento ya entregado al
# cliente podía dejar de marcar la diferencia que marcaba, porque alguien corrigió la ficha
# después. Un entregable no puede cambiar solo.
#
# Mientras la revisión es borrador siguen a la ficha, que es lo correcto: se está comparando
# contra la especificación vigente. Al confirmar se vuelve un documento y quedan fijos.
CAMPOS_FICHA_CONGELADOS = {
    "luces_ficha": "mc_cantidad_luces",
    "software_ficha_id": "mc_software_superficie",
    "version_software_ficha": "mc_version_software",
    "version_ardusub_ficha": "mc_version_ardusub",
    "controlador_ficha_id": "mc_controlador_vuelo",
    "version_controlador_ficha": "mc_version_controlador",
    "umbilical_ficha": "mc_n_serie_umbilical",
    "largo_ficha": "mc_longitud",
    "diametro_ficha": "mc_diametro",
}

# Las condiciones bajo las que se corrió la prueba, que una revisión nueva hereda de la
# anterior del mismo equipo. **Solo condiciones, nunca resultados**: heredar una medición
# sería inventar un dato, mientras que heredar con qué se alimentó es recordar cómo está
# montado el taller. En el taller la fuente es la que es, y un ROV que vuelve cinco veces
# obligaba a contestar cinco veces lo mismo — y la quinta se contesta de memoria, que es
# cuando aparecen los datos malos.
CONDICIONES_HEREDABLES = (
    "umbilical",
    "largo",
    "alimentacion",
    "modelo_fuente",
    "tension_salida",
)

# De quién hereda cada tipo. Una prueba en terreno **no** hereda de una de taller ni al revés:
# la alimentación de un muelle no dice nada de la de un banco.
# **La reparación no hereda de nadie.** En una prueba de aceptación repetida sobre el mismo
# equipo, la alimentación y el cable son el montaje del taller y volver a teclearlos es
# trámite. En una reparación no: ahí esas condiciones son **parte de lo que hay que
# comprobar** —con qué cable llegó, qué entrega su fuente— y precargarlas sería contestar por
# el técnico justo la pregunta que vino a responder. Mismo criterio por el que el software
# tampoco se precarga en reparación.
FAMILIAS_DE_CONDICIONES = (
    ("rendimiento",),
    ("terreno",),
)

# Qué campo de la prueba alimenta qué campo de la ficha del equipo, y desde qué tipos.
#
# **La regla que decide qué entra acá:** el volcado vale cuando la prueba es el único origen
# de ese valor, y NO vale cuando la ficha es la referencia contra la que la prueba compara —
# ahí escribir la ficha borraría justamente la diferencia que se quería ver. Por eso el conteo
# de luces no está en esta tabla y no debe agregarse: la ficha dice cuántas luces debería
# tener el equipo, y una luz quemada se volvería la nueva especificación.

# El software solo lo determina la prueba de rendimiento: es donde se instala. **Y viaja en
# los dos sentidos**: la prueba nace con lo que la ficha ya declara, y al confirmarse le
# devuelve lo que se encontró. Así el orden de trabajo deja de importar — se llene primero la
# ficha o primero la prueba, nadie teclea lo mismo dos veces.
SOFTWARE_A_FICHA = {
    "software_instalado_id": "mc_software_superficie",
    "version_software_instalada": "mc_version_software",
    "version_ardusub_instalada": "mc_version_ardusub",
    "controlador_instalado_id": "mc_controlador_vuelo",
    "version_controlador_instalada": "mc_version_controlador",
}

# Los ajustes se confirman en las tres, así que manda la revisión más reciente del equipo sea
# del tipo que sea.
AJUSTES_A_FICHA = {
    "limitacion_pilot_gain": "mc_limitacion_pilot_gain",
    "ganancia_luz": "mc_ganancia_luz",
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
    luces_ficha = fields.Integer(string="Luces según ficha", readonly=True)
    luces_difieren = fields.Boolean(
        string="El conteo no cuadra", compute="_compute_luces", store=True
    )

    # --- Lo que la ficha declara instalado ---
    #
    # Entran en 19.0.15.2.0 junto al chequeo "El software instalado corresponde a la ficha".
    # Son `related` de solo lectura y no copias: el dato vive en el número de serie y ahí se
    # edita.
    #
    # Existen por una razón de pantalla, no de modelo. El chequeo se responde comparando
    # contra la ficha, y si para responderlo hay que abrir el número de serie y volver, se
    # responde "OK" sin mirar — que es peor que no preguntar, porque deja un dato falso donde
    # antes había un vacío honesto.
    #
    # A diferencia de las luces, acá NO hay un `difieren` calculado. Con el nombre del
    # software escrito a mano, "QGround" y "QGroundControl" son la misma cosa y darían falso
    # positivo; y sobre todo, todavía no se sabe cuál de los tres revierte. La comparación la
    # hace el ojo, que para tres líneas es suficiente y no se equivoca con la ortografía.
    software_ficha_id = fields.Many2one(
        "mc.rov.software.superficie",
        string="Software de superficie",
        readonly=True,
    )
    version_software_ficha = fields.Char(
        string="Versión del software",
        readonly=True,
    )
    version_ardusub_ficha = fields.Char(string="Versión ArduSub", readonly=True)
    controlador_ficha_id = fields.Many2one(
        "mc.rov.controlador.vuelo",
        string="Controlador de vuelo",
        readonly=True,
    )
    version_controlador_ficha = fields.Char(
        string="Versión del controlador",
        readonly=True,
    )

    # La misma idea que `luces_difieren`: la ficha dice lo que el equipo DEBERÍA tener, la
    # revisión anota lo que se encontró, y la diferencia es el hallazgo. **No se vuelca a la
    # ficha**: encontrar otra versión no es haberla cambiado — es que el equipo revirtió o lo
    # actualizaron fuera, y eso se registra, no se normaliza.
    software_difiere = fields.Boolean(
        string="El software no cuadra con la ficha",
        compute="_compute_software_difiere",
        store=True,
    )

    @api.depends(
        "version_software_instalada",
        "version_ardusub_instalada",
        "version_controlador_instalada",
        "version_software_ficha",
        "version_ardusub_ficha",
        "version_controlador_ficha",
    )
    def _compute_software_difiere(self):
        """Solo compara lo que la revisión anotó: un campo vacío no afirma nada.

        Sin esa condición, una revisión a medio llenar marcaría diferencia contra todo lo que
        la ficha declara — el mismo vacío-indistinguible-de-dato que el módulo persigue en
        todas partes.
        """
        pares = (
            ("version_software_instalada", "version_software_ficha"),
            ("version_ardusub_instalada", "version_ardusub_ficha"),
            ("version_controlador_instalada", "version_controlador_ficha"),
        )
        for revision in self:
            revision.software_difiere = any(
                revision[encontrado] and revision[encontrado] != revision[ficha]
                for encontrado, ficha in pares
            )

    # --- Software instalado, y va al revés que en reparación ---
    #
    # En reparación el software se COMPARA: la ficha es la referencia y la revisión contrasta
    # (los cinco `related` de arriba). En la prueba de rendimiento no hay contra qué comparar —el
    # equipo acaba de nacer y su ficha está vacía— así que **la prueba determina el valor y la
    # ficha lo recibe** (§ 5.4).
    software_instalado_id = fields.Many2one(
        "mc.rov.software.superficie", string="Software de superficie instalado"
    )
    version_software_instalada = fields.Char(string="Versión del software instalada")
    version_ardusub_instalada = fields.Char(string="Versión ArduSub instalada")
    controlador_instalado_id = fields.Many2one(
        "mc.rov.controlador.vuelo", string="Controlador de vuelo instalado"
    )
    version_controlador_instalada = fields.Char(string="Versión del controlador instalada")

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
    # Solo cuando el cable es del taller. Si es el del equipo, su largo ya está en la ficha
    # y pedirlo otra vez es teclear dos veces el mismo dato — el § 5.4 lo dice así:
    # «umbilical usado, y largo solo si es del taller».
    largo = fields.Float(string="Largo del umbilical (m)")

    # El cable del equipo, traído de la ficha. En una prueba de aceptación se prueba con el
    # umbilical propio, así que estos tres datos ya están definidos y no hay por qué volver a
    # teclearlos — se muestran para saber con qué se probó. El peso no: no dice nada de la
    # prueba. Si el cable es del taller, esto no aplica y el largo se pide a mano.
    # Con qué cable llegó el equipo, para contrastarlo con el que su ficha declara. Es la
    # tercera comparación de la misma familia —la ficha dice lo que el equipo debería tener,
    # la visita dice lo que llegó— y era la única que faltaba: hasta 19.0.18.3.0 la revisión
    # solo sabía «del equipo / del taller», nunca cuál.
    #
    # Un ROV que llega con otro umbilical es un hallazgo: se lo cambiaron, lo perdieron, o
    # pusieron uno prestado. Sin este campo eso no se veía nunca.
    umbilical_serie = fields.Char(string="N° de serie del umbilical recibido")

    umbilical_difiere = fields.Boolean(
        string="El umbilical no cuadra con la ficha",
        compute="_compute_umbilical_difiere",
        store=True,
    )

    @api.depends("umbilical", "umbilical_serie", "umbilical_ficha")
    def _compute_umbilical_difiere(self):
        """Solo compara cuando hay contra qué, y cuando el cable es el del equipo.

        Con el del taller no hay nada que comparar —ya se sabe que no es el suyo— y con
        cualquiera de los dos números vacío tampoco: un campo sin llenar no afirma nada.
        """
        for revision in self:
            revision.umbilical_difiere = bool(
                revision.umbilical == "equipo"
                and revision.umbilical_serie
                and revision.umbilical_ficha
                and revision.umbilical_serie != revision.umbilical_ficha
            )

    umbilical_ficha = fields.Char(
        string="N° de serie del umbilical",
        readonly=True,
    )
    largo_ficha = fields.Float(
        string="Largo según ficha (m)",
        readonly=True,
    )
    diametro_ficha = fields.Float(
        string="Diámetro según ficha (mm)",
        readonly=True,
    )

    alimentacion = fields.Selection(
        [("UPS", "UPS"), ("Generador", "Generador"), ("Transformador", "Transformador")],
        string="Alimentación",
    )
    tension_salida = fields.Integer(string="Tensión de salida (V)")

    # El resultado es binario —el ROV corre 1 a 1½ horas en un bin con agua y
    # o aguanta o presenta problemas— pero cuánto aguantó es información distinta y
    # comparable. "Aguantó 90 minutos" y "falló a los 15" quedarían registrados igual sin la
    # duración. Si falló, es tiempo hasta la falla; si pasó, es la fuerza de la evidencia.
    funcionamiento_continuo_duracion = fields.Float(
        string="Duración de la corrida (h)", digits=(5, 2)
    )
    funcionamiento_continuo_resultado = fields.Selection(
        [("ok", "Sin problemas"), ("con_problemas", "Presentó problemas")],
        string="Resultado del funcionamiento continuo",
    )

    # No hay campo "ancho de banda": ese es el nombre de la prueba, no una tercera medición.
    # El «±5%» del nombre viejo de la ficha era una referencia para quien juzga, no un dato,
    # así que baja al help: el sistema guarda la medición y no opina sobre ella mientras no
    # tenga con qué (§ 5.6).
    subida = fields.Float(
        string="Subida (Mbps)",
        digits=(6, 2),
        help="El valor de referencia puede variar ±5%. Lo juzga el técnico.",
    )
    bajada = fields.Float(
        string="Bajada (Mbps)",
        digits=(6, 2),
        help="El valor de referencia puede variar ±5%. Lo juzga el técnico.",
    )

    modelo_fuente = fields.Char(string="Modelo de fuente")

    # Cuánto duró la prueba entera. **No es `funcionamiento_continuo_duracion`**: ésa es la
    # corrida de resistencia DENTRO de la prueba. Una prueba en terreno de tres horas puede no
    # llevar corrida; una de rendimiento lleva las dos y son números distintos (§ 4.7).
    duracion = fields.Float(string="Duración total (h)", digits=(5, 2))

    # Se llama «Condiciones y notas» y **no «Observaciones»**, y el nombre es parte del
    # diseño: *observaciones* es una invitación a escribir aquí los hallazgos, y eso mataría
    # el catálogo que costó dos versiones construir. Acá va lo que hace falta para interpretar
    # los resultados y no cabe en ningún chequeo — la marea, que el cliente pidió cortar
    # antes, que el generador andaba justo.
    condiciones_notas = fields.Text(
        string="Condiciones y notas de la prueba",
        help="Lo que hace falta para interpretar los resultados y no cabe en ningún chequeo. "
        "Los hallazgos van en su pestaña.",
    )

    # --- Estanqueidad ---
    #
    # Son la medición al lado del chequeo, no en su lugar: quien dice si estanco aprobó es el
    # chequeo «Estanqueidad bajo presión», que responde OK / No OK / No aplica. Estos dos
    # números lo acompañan y no opinan.
    #
    # **Sin umbral, a propósito.** El estándar existe —2 h a 30 bar, 50 en algunos modelos,
    # eventualmente hasta 100— y aun así no se declara por modelo: los técnicos saben a cuánto
    # va cada equipo, y exigir el valor por adelantado es agregarle trámite a algo que ya
    # funciona (§ 5.6). En terreno esta pareja no aplica: ahí la verificación de presión es la
    # profundidad alcanzada, que es la misma pregunta por otro medio.
    presion_bar = fields.Float(string="Presión alcanzada (bar)", digits=(6, 1))
    presion_tiempo = fields.Float(string="Tiempo a presión (h)", digits=(5, 2))

    # --- Bloque eléctrico ---
    #
    # Las tres van juntas porque se leen juntas: una fuga alta con consumos normales dice algo
    # distinto de una fuga alta con el consumo disparado.
    fuga_corriente = fields.Float(string="Fuga de corriente (A)", digits=(6, 3))
    consumo_reposo = fields.Float(string="Consumo en reposo (kWh)", digits=(6, 2))
    # Se llamaba «esfuerzo» en la ficha del lote. La palabra significaba tres cosas a la vez
    # y se retiró entera (§ 5.5): esto es un consumo, y la corrida de hora y media es otra
    # cosa que ahora se llama funcionamiento continuo.
    consumo_carga = fields.Float(string="Consumo bajo carga (kWh)", digits=(6, 2))

    # --- Parámetros de trabajo ---
    #
    # Se miden en las TRES: el taller también los ajusta al reparar (confirmado 2026-08-21,
    # corrige lo que decía el § 5.4). Por eso no hay bloque de comparación — la ficha recibe el
    # valor de la prueba más reciente sea del tipo que sea, y el último ajuste es la verdad.
    #
    # A diferencia del conteo de luces, donde la ficha dice cuántas DEBERÍA tener el equipo y
    # la diferencia con lo que encendió ES el hallazgo. Por eso ése no se vuelca nunca.
    limitacion_pilot_gain = fields.Integer(string="Limitación pilot gain (%)")
    ganancia_luz = fields.Integer(string="Ganancia luz (%)")

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
        help="Se deriva de los chequeos, el funcionamiento continuo y los hallazgos. No es "
        "editable: un "
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
        "tipo",
        "chequeo_ids.resultado",
        "funcionamiento_continuo_resultado",
        "hallazgo_ids.severidad",
    )
    def _compute_resultado(self):
        """El orden de las condiciones es la regla de negocio.

        Un chequeo fallado o un funcionamiento continuo con problemas rechazan la revisión
        aunque no se
        haya registrado ningún hallazgo: el equipo no pasó, y eso no se compensa con que
        nadie haya escrito por qué.

        **Y una revisión a medio llenar no dice nada: queda vacía.** Hasta 19.0.15.1.0 caía
        en «Aprobado» por descarte, así que una ficha recién creada —con los 22 chequeos sin
        responder y nada probado— declaraba que el equipo estaba bien. Es el vacío
        indistinguible de un dato, y encima del lado optimista.
        """
        for revision in self:
            sin_responder = any(not linea.resultado for linea in revision.chequeo_ids)
            # Se exige solo donde es parte de la batería. Exigirlo siempre
            # dejaba a las revisiones de terreno sin resultado posible.
            falta_continuo = (
                revision.tipo in TIPOS_CON_FUNCIONAMIENTO_CONTINUO
                and not revision.funcionamiento_continuo_resultado
            )
            if sin_responder or falta_continuo:
                revision.resultado = False
                continue

            rechaza = (
                any(linea.resultado == "no_ok" for linea in revision.chequeo_ids)
                or revision.funcionamiento_continuo_resultado == "con_problemas"
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
            # Nace con las condiciones de la prueba anterior del mismo equipo. Mismo criterio
            # que la fecha, que nace con la de hoy: un valor corregible sirve más que un campo
            # en blanco. Solo rellena lo que no venga ya en `vals`.
            self._heredar_condiciones(vals)
            self._precargar_desde_la_ficha(vals)

        revisiones = super().create(vals_list)
        revisiones._refrescar_ficha()
        for revision in revisiones:
            self._generar_chequeos(revision)
            self._generar_inspeccion(revision)
        return revisiones

    def unlink(self):
        """Una revisión confirmada no se borra: es evidencia, y un entregable al cliente.

        Los borradores sí, porque el botón del número de serie crea al primer clic y hace
        falta poder deshacer un clic equivocado.
        """
        confirmadas = self.filtered(lambda revision: revision.estado == "confirmado")
        if confirmadas:
            nombres = ", ".join(confirmadas.mapped("display_name"))
            raise UserError(
                "Estas revisiones están confirmadas y no se pueden borrar:\n\n"
                f"{nombres}\n\n"
                "Vuélvelas a borrador si hay que corregirlas."
            )
        return super().unlink()

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

        # La corrida siempre se hace, incluso cuando la revisión existe solo para
        # comparar un cable: el taller confirmó que nunca se cambia el umbilical solo para
        # medir ancho de banda.
        if not revision.funcionamiento_continuo_resultado:
            faltan.append("el resultado del funcionamiento continuo")
        if (
            revision.funcionamiento_continuo_resultado
            and not revision.funcionamiento_continuo_duracion
        ):
            faltan.append("cuánto duró el funcionamiento continuo")
        if not revision.alimentacion:
            faltan.append("la alimentación usada")
        # Solo se exige para el cable del taller: el del equipo ya declara su largo en la
        # ficha, y exigirlo acá obligaría a copiarlo a mano en cada revisión.
        if revision.umbilical == "prueba" and not revision.largo:
            faltan.append("el largo del umbilical del taller con el que se probó")
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

    @api.model
    def _heredar_condiciones(self, vals):
        lot_id, tipo = vals.get("lot_id"), vals.get("tipo")
        familia = next((f for f in FAMILIAS_DE_CONDICIONES if tipo in f), None)
        if not lot_id or not familia:
            return

        anterior = self.search(
            [("lot_id", "=", lot_id), ("tipo", "in", list(familia))],
            order="fecha desc, id desc",
            limit=1,
        )
        if not anterior:
            return

        for campo in CONDICIONES_HEREDABLES:
            if campo in vals:
                continue
            valor = anterior[campo]
            if valor:
                vals[campo] = valor

    @api.model
    def _precargar_desde_la_ficha(self, vals):
        """La prueba de rendimiento nace con lo que la ficha ya declara.

        Es la otra mitad del volcado, y junta con él hace que **el orden de trabajo deje de
        importar**: si alguien llena la ficha primero, la prueba llega con esos valores y no
        los vuelve a pedir; si hace la prueba primero, la ficha los recibe al confirmar.

        Solo para la prueba de rendimiento, que es la que determina el software. En
        reparación estos campos son de comparación y precargarlos borraría la diferencia que
        se quiere ver.
        """
        if vals.get("tipo") != "rendimiento" or not vals.get("lot_id"):
            return
        lot = self.env["stock.lot"].browse(vals["lot_id"])
        for campo_prueba, campo_ficha in SOFTWARE_A_FICHA.items():
            if campo_prueba in vals:
                continue
            valor = lot[campo_ficha]
            if valor:
                vals[campo_prueba] = valor.id if hasattr(valor, "id") else valor

    def _refrescar_ficha(self):
        """Toma la foto de lo que la ficha declara ahora.

        Se llama en dos momentos y solo en dos: **al crear la revisión** —para que el técnico
        vea contra qué está comparando desde el primer minuto— y **al confirmar**, que es
        cuando la revisión deja de ser un borrador y pasa a ser un documento.

        A partir de ahí no se toca nunca más, y ésa es toda la razón de que estos campos
        existan. Hasta 19.0.18.2.0 eran `related` en vivo: una revisión de hace seis meses
        mostraba la ficha de hoy, y `luces_difieren` se recalculaba — o sea que un documento
        ya entregado al cliente podía dejar de marcar la diferencia que marcó el día de la
        prueba. Un entregable no puede contradecirse a sí mismo.
        """
        for revision in self:
            if not revision.lot_id:
                continue
            revision.write(
                {
                    campo: revision.lot_id[campo_lote]
                    for campo, campo_lote in CAMPOS_FICHA_CONGELADOS.items()
                }
            )

    def action_confirmar(self):
        """Cierra la revisión. A partir de aquí el registro es evidencia, no borrador."""
        for revision in self:
            faltan = self._faltantes_para_confirmar(revision)
            if faltan:
                detalle = "\n".join(f"· {item}" for item in faltan)
                raise UserError(
                    f"Falta lo siguiente para confirmar {revision.display_name}:\n\n{detalle}"
                )
            # La foto de la ficha se refresca ANTES de marcar confirmado: después ya no
            # se toca, y lo que quede aquí es lo que el documento va a decir para siempre.
            revision._refrescar_ficha()
            revision.estado = "confirmado"
            revision._volcar_a_la_ficha()

    def _volcar_a_la_ficha(self):
        """La prueba escribe en la ficha lo que sólo ella sabe.

        Dos volcados con reglas distintas, y la diferencia importa:

        - **El software lo determina la prueba de rendimiento**, porque es donde se instala. En
          reparación se compara contra la ficha; acá es al revés, y si esto no ocurriera la
          ficha quedaría vacía **y la comparación del lado de reparación no funcionaría nunca**.
        - **Los ajustes —pilot gain y ganancia luz— se confirman en las tres**, incluida la
          reparación: el taller también los ajusta al reparar. Manda la revisión más reciente
          del equipo, sea del tipo que sea.

        **En los dos casos sobrescribe, y solo desde la prueba más reciente.** Sobrescribir es
        lo correcto: dejar un valor viejo haría que cada revisión posterior registrara una
        diferencia falsa. Lo que no puede pasar es que corregir una prueba antigua pise la
        ficha de hoy — confirmar no ocurre en orden cronológico. Por eso manda la más reciente
        y no la que se está confirmando, mismo criterio que `ultima_mantencion`.

        Y queda en el chatter del equipo: escribir en la ficha de otro registro sin dejar
        rastro es justo lo que este módulo evita.
        """
        self.ensure_one()
        if not self.lot_id:
            return

        valores = {}
        if self._es_la_mas_reciente(tipos=("rendimiento",)):
            valores.update(self._valores_para_la_ficha(SOFTWARE_A_FICHA))
        if self._es_la_mas_reciente(tipos=TODOS_LOS_TIPOS):
            valores.update(self._valores_para_la_ficha(AJUSTES_A_FICHA))
        if not valores:
            return

        self.lot_id.write(valores)
        nombres = ", ".join(self.lot_id._fields[campo].string for campo in valores)
        self.lot_id.message_post(body=f"Ficha actualizada desde {self.display_name}: {nombres}.")

    def _es_la_mas_reciente(self, tipos):
        """Si esta revisión es la última confirmada del equipo entre los tipos que se le pasen."""
        self.ensure_one()
        if self.tipo not in tipos:
            return False
        dominio = [
            ("lot_id", "=", self.lot_id.id),
            ("estado", "=", "confirmado"),
            ("tipo", "in", list(tipos)),
        ]
        return self.search(dominio, order="fecha desc, id desc", limit=1) == self

    def _valores_para_la_ficha(self, mapa):
        """Lo que hay que escribir, saltando lo que no se anotó y lo que ya coincide.

        Un campo vacío en la prueba no es una afirmación sobre el equipo: no borra la ficha.
        """
        self.ensure_one()
        valores = {}
        for campo_prueba, campo_ficha in mapa.items():
            valor = self[campo_prueba]
            if not valor:
                continue
            valor = valor.id if hasattr(valor, "id") else valor
            if self.lot_id[campo_ficha] != valor:
                valores[campo_ficha] = valor
        return valores

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
    # `related` al catálogo y no un entero propio. Era `fields.Integer(default=10)`, o sea
    # **el mismo valor en todas las líneas**, así que `_order` caía a `id` y la ficha se
    # mostraba en orden de creación. Dos consecuencias que se veían en pantalla y que nadie
    # relacionaba con esto:
    #
    # 1. Un chequeo agregado al catálogo después quedaba **último para siempre**, aunque su
    #    secuencia lo pusiera al medio. «Movimiento horizontal» (sequence 66) salía detrás de
    #    «Sin ruido ni vibración» (77).
    # 2. **Reordenar el catálogo no tenía ningún efecto sobre las revisiones ya creadas.** En
    #    19.0.14.2.0 se movió *stabilize* antes de *depth hold* para que la batería contara
    #    una historia —si estabiliza pero no mantiene profundidad, apunta al sensor de
    #    presión— y ese cambio no llegó a ninguna ficha existente.
    #
    # Almacenado porque `_order` no puede ordenar por un campo que no vive en la tabla, e
    # indexado porque se ordena por él en cada apertura de la ficha.
    sequence = fields.Integer(related="chequeo_id.sequence", store=True, index=True)

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
    # Se llamaba `observacion` hasta 19.0.16.0.0. Había tres nombres para la misma idea —
    # `detalle` en la línea de chequeo, `detalle` en la de hallazgo, y `observacion` acá— y
    # esta versión lleva migración de todos modos, así que unificarlo salió gratis.
    detalle = fields.Char(string="Detalle")

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
