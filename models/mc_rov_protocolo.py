from odoo import models, fields, api
from odoo.exceptions import UserError

TIPOS = [
    ("fabricacion", "Fabricación"),
    ("recepcion", "Recepción"),
    ("entrega", "Entrega"),
    ("terreno", "Prueba en terreno"),
]

# Qué campo del catálogo de chequeos habilita cada tipo de protocolo. Se lee de aquí en vez
# de encadenar ifs, para que agregar un tipo sea tocar dos listas y no buscar condicionales
# repartidos por el archivo.
CAMPO_APLICA = {
    "fabricacion": "aplica_fabricacion",
    "recepcion": "aplica_recepcion",
    "entrega": "aplica_entrega",
    "terreno": "aplica_terreno",
}

RESULTADOS_CHEQUEO = [
    ("ok", "OK"),
    ("no_ok", "No OK"),
    # "No lo tiene" y no "No aplica": afirma algo sobre el equipo, no sobre lo que hizo el
    # técnico. La inspección física no siempre recorre los cinco componentes —no todos los
    # ROV llevan joystick, y el cilindro fuente solo existe en los que tienen dos e-pods— y
    # "No aplica" dejaría el registro diciendo a la vez "el equipo no lo tiene" y "no lo
    # revisamos". Con eso se pierde el denominador de cualquier estadística.
    ("no_lo_tiene", "No lo tiene"),
]

SEVERIDADES = [
    ("informativo", "Informativo"),
    ("atencion", "Requiere atención"),
    ("impide_operar", "Impide operar"),
]


class McRovProtocolo(models.Model):
    """Una sesión de pruebas sobre un equipo: la ficha de reparación, digital.

    Reemplaza la hoja de papel del taller. Lo que esa hoja registra bien es **qué se
    probó**; lo que registra mal son los hallazgos, que caen todos en un campo de
    observaciones en texto libre y por eso no se pueden contar ni comparar.

    Cuelga del número de serie y no de la orden de reparación **a propósito**: un ROV nuevo
    pasa por la misma batería antes de despacharse y ahí no hay orden. Si colgara de la
    orden, toda la fabricación quedaría fuera del análisis.
    """

    _name = "mc.rov.protocolo"
    _description = "Protocolo de pruebas ROV"
    _inherit = ["mail.thread"]
    _order = "fecha desc, id desc"
    _rec_name = "name"

    name = fields.Char(string="Protocolo", readonly=True, copy=False, default="/")

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
        help="La visita al taller, si la hubo. Vacío en los protocolos de fabricación, que "
        "ocurren antes de que exista ninguna orden.",
    )

    tipo = fields.Selection(TIPOS, string="Tipo", required=True, default="recepcion")

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
        "análisis es la diferencia entre dos protocolos: las horas que voló entre una "
        "visita y la siguiente.",
    )

    # --- Derivados: el protocolo no guarda contactos propios ---

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

    temperatura_interior = fields.Float(string="Temperatura interior (°C)")
    temperatura_exterior = fields.Float(string="Temperatura exterior (°C)")

    # --- Solo en pruebas de terreno ---

    lugar = fields.Char(string="Lugar")
    profundidad = fields.Integer(string="Profundidad (m)")
    velocidad_corriente = fields.Float(string="Velocidad de la corriente (kn)")

    # --- Líneas ---

    corrida_ids = fields.One2many("mc.rov.protocolo.corrida", "protocolo_id", string="Corridas")
    chequeo_ids = fields.One2many("mc.rov.protocolo.chequeo", "protocolo_id", string="Chequeos")
    hallazgo_ids = fields.One2many("mc.rov.protocolo.hallazgo", "protocolo_id", string="Hallazgos")

    resultado = fields.Selection(
        [
            ("aprobado", "Aprobado"),
            ("aprobado_con_observaciones", "Aprobado con observaciones"),
            ("rechazado", "Rechazado"),
        ],
        string="Resultado",
        compute="_compute_resultado",
        store=True,
        help="Se deriva de los chequeos, las corridas y los hallazgos. No es editable: un "
        "override sería el texto libre de vuelta, en otra forma.",
    )

    @api.depends("luces_internas", "luces_externas", "luces_ficha")
    def _compute_luces(self):
        """El conteo de la prueba contra la especificación del equipo.

        Si el ROV debería tener seis luces y se contaron cuatro, el sistema lo dice sin que
        nadie tenga que acordarse de comparar. Es una de las cosas que la inspección busca.
        """
        for protocolo in self:
            protocolo.luces_total = protocolo.luces_internas + protocolo.luces_externas
            protocolo.luces_difieren = bool(protocolo.luces_ficha) and (
                protocolo.luces_total != protocolo.luces_ficha
            )

    @api.depends(
        "chequeo_ids.resultado",
        "corrida_ids.esfuerzo_resultado",
        "hallazgo_ids.severidad",
    )
    def _compute_resultado(self):
        """El orden de las condiciones es la regla de negocio.

        Un chequeo fallado o un esfuerzo con problemas rechazan el protocolo aunque no se
        haya registrado ningún hallazgo: el equipo no pasó, y eso no se compensa con que
        nadie haya escrito por qué.
        """
        for protocolo in self:
            rechaza = (
                any(linea.resultado == "no_ok" for linea in protocolo.chequeo_ids)
                or any(
                    corrida.esfuerzo_resultado == "con_problemas"
                    for corrida in protocolo.corrida_ids
                )
                or any(
                    hallazgo.severidad == "impide_operar" for hallazgo in protocolo.hallazgo_ids
                )
            )
            if rechaza:
                protocolo.resultado = "rechazado"
            elif protocolo.hallazgo_ids:
                protocolo.resultado = "aprobado_con_observaciones"
            else:
                protocolo.resultado = "aprobado"

    # --- Generación del checklist ---

    def _chequeos_del_tipo(self, tipo):
        """Los chequeos activos del catálogo que corresponden a este tipo de protocolo."""
        campo = CAMPO_APLICA.get(tipo)
        if not campo:
            return self.env["mc.rov.chequeo"]
        return self.env["mc.rov.chequeo"].search([(campo, "=", True)])

    def _generar_chequeos(self, protocolo):
        """Crea las líneas de checklist que falten para el tipo del protocolo.

        Las genera el sistema y no la persona porque el punto de un checklist es que
        siempre traiga los mismos ítems: si el técnico eligiera cuáles agregar, no habría
        forma de distinguir "revisado y limpio" de "no se me ocurrió mirarlo".

        Solo agrega lo que falta y nunca borra respuestas. Un chequeo respondido sobrevive
        aunque cambie el tipo del protocolo, porque el dato ya se levantó y perderlo sería
        peor que tener una línea de más.

        Recibe el protocolo como argumento en vez de operar sobre self: lo llaman create y
        write sobre un registro a la vez, siguiendo la convención del módulo.
        """
        Linea = self.env["mc.rov.protocolo.chequeo"]
        # Solo los marcados como inspeccionables: sin ese filtro un chequeo "por componente"
        # generaría una línea por cada entrada del catálogo, incluidos umbilical, cámara o
        # sensor, que no se revisan buscando sellos de terceros.
        componentes = self.env["mc.rov.componente"].search([("es_inspeccionable", "=", True)])
        existentes = {
            (linea.chequeo_id.id, linea.componente_id.id) for linea in protocolo.chequeo_ids
        }

        valores = []
        for chequeo in self._chequeos_del_tipo(protocolo.tipo):
            objetivos = componentes if chequeo.por_componente else [False]
            for componente in objetivos:
                componente_id = componente.id if componente else False
                if (chequeo.id, componente_id) in existentes:
                    continue
                valores.append(
                    {
                        "protocolo_id": protocolo.id,
                        "chequeo_id": chequeo.id,
                        "componente_id": componente_id,
                        "sequence": chequeo.sequence,
                    }
                )

        if valores:
            Linea.create(valores)

    def _limpiar_chequeos_sin_responder(self, protocolo):
        """Borra las líneas que dejaron de corresponder y que nadie contestó.

        Solo las sin responder: cambiar el tipo de un protocolo a medio llenar no debe
        borrar trabajo hecho.
        """
        validos = self._chequeos_del_tipo(protocolo.tipo)
        sobrantes = protocolo.chequeo_ids.filtered(
            lambda linea: not linea.resultado and linea.chequeo_id not in validos
        )
        sobrantes.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("mc.rov.protocolo") or "/"

        protocolos = super().create(vals_list)
        for protocolo in protocolos:
            self._generar_chequeos(protocolo)
        return protocolos

    def write(self, vals):
        res = super().write(vals)
        if "tipo" in vals:
            for protocolo in self:
                self._limpiar_chequeos_sin_responder(protocolo)
                self._generar_chequeos(protocolo)
        return res

    # --- Confirmación ---

    def _faltantes_para_confirmar(self, protocolo):
        """Qué le impide a este protocolo pasar a confirmado, en lenguaje del taller.

        Se devuelve una lista y no el primer problema encontrado: hacer que el técnico
        descubra los faltantes de a uno, guardando entre medio, es la forma más segura de
        que abandone.
        """
        faltan = []

        if not protocolo.responsable_id:
            faltan.append("indicar el responsable")

        if not protocolo.corrida_ids:
            faltan.append("registrar al menos una corrida (la prueba de esfuerzo siempre se hace)")

        for corrida in protocolo.corrida_ids:
            etiqueta = corrida.display_name
            if not corrida.esfuerzo_resultado:
                faltan.append(f"el resultado del esfuerzo en {etiqueta}")
            if corrida.esfuerzo_resultado and not corrida.esfuerzo_duracion:
                faltan.append(f"cuánto duró el esfuerzo en {etiqueta}")
            if not corrida.alimentacion:
                faltan.append(f"la alimentación usada en {etiqueta}")
            if bool(corrida.subida) != bool(corrida.bajada):
                faltan.append(f"la subida y la bajada en {etiqueta} — o ambas, o ninguna")

        sin_responder = protocolo.chequeo_ids.filtered(lambda linea: not linea.resultado)
        if sin_responder:
            faltan.append(f"responder {len(sin_responder)} chequeo(s) pendiente(s)")

        return faltan

    def action_confirmar(self):
        """Cierra el protocolo. A partir de aquí el registro es evidencia, no borrador."""
        for protocolo in self:
            faltan = self._faltantes_para_confirmar(protocolo)
            if faltan:
                detalle = "\n".join(f"· {item}" for item in faltan)
                raise UserError(
                    f"Falta lo siguiente para confirmar {protocolo.display_name}:\n\n{detalle}"
                )
            protocolo.estado = "confirmado"

    def action_volver_a_borrador(self):
        """Reabre un protocolo confirmado. Existe porque las fichas se equivocan.

        Queda en el chatter, que es lo que distingue una corrección de un borrado.
        """
        for protocolo in self:
            protocolo.estado = "borrador"
            protocolo.message_post(body="El protocolo volvió a borrador para corregirse.")


class McRovProtocoloCorrida(models.Model):
    """Una pasada de pruebas con un umbilical determinado.

    Existe como modelo aparte porque **el umbilical es una condición de la corrida y no un
    dato de una prueba**. Normalmente hay una sola, con el cable del propio equipo. Hay dos
    cuando se usa además el umbilical de prueba estándar como muestra de control, y
    entonces la comparación entre líneas aísla el cable como fuente de falla: mismo ROV,
    mismo banco, distinto cable. Si el ancho de banda solo cae con el umbilical propio, el
    problema es el cable y no el vehículo.

    Lo que no depende del cable —inspección física, presión, leak, luces, video— vive en el
    protocolo y se hace una sola vez aunque haya dos corridas.
    """

    _name = "mc.rov.protocolo.corrida"
    _description = "Corrida de pruebas con un umbilical"
    _order = "protocolo_id, sequence, id"

    protocolo_id = fields.Many2one(
        "mc.rov.protocolo", string="Protocolo", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(default=10)

    umbilical = fields.Selection(
        [("equipo", "Del equipo"), ("prueba", "De prueba (control)")],
        string="Umbilical",
        required=True,
        default="equipo",
    )
    largo = fields.Float(string="Largo (m)", required=True)

    alimentacion = fields.Selection(
        [("UPS", "UPS"), ("Generador", "Generador"), ("Transformador", "Transformador")],
        string="Alimentación",
    )
    tension_salida = fields.Integer(string="Tensión de salida (V)")

    # El resultado del esfuerzo es binario —el ROV corre 1 a 1½ horas en un bin con agua y
    # o aguanta o presenta problemas— pero cuánto aguantó es información distinta y
    # comparable. "Aguantó 90 minutos" y "falló a los 15" hoy quedan registrados igual, o
    # sea, no registrados. Si falló, la duración es tiempo hasta la falla; si pasó, es la
    # fuerza de la evidencia.
    esfuerzo_duracion = fields.Float(string="Duración del esfuerzo (h)", digits=(5, 2))
    esfuerzo_resultado = fields.Selection(
        [("ok", "Sin problemas"), ("con_problemas", "Presentó problemas")],
        string="Resultado del esfuerzo",
    )

    # No hay campo "ancho de banda": ese es el nombre de la prueba, no una tercera medición.
    subida = fields.Float(string="Subida (Mbps)", digits=(6, 2))
    bajada = fields.Float(string="Bajada (Mbps)", digits=(6, 2))

    def _compute_display_name(self):
        for corrida in self:
            etiqueta = dict(corrida._fields["umbilical"].selection).get(corrida.umbilical, "")
            corrida.display_name = f"{etiqueta} · {corrida.largo:g} m"


class McRovProtocoloChequeo(models.Model):
    """Una línea del checklist: qué se revisó y qué salió.

    El campo `resultado` cubre dos dimensiones con un solo valor, porque la ficha de papel
    registra principalmente *qué se testeó* y no *qué resultó*. Vacío significa que todavía
    no se responde —y eso impide confirmar—, mientras que «No lo tiene» es una respuesta
    válida y de uso corriente.
    """

    _name = "mc.rov.protocolo.chequeo"
    _description = "Línea de chequeo de un protocolo"
    _order = "protocolo_id, sequence, id"

    protocolo_id = fields.Many2one(
        "mc.rov.protocolo", string="Protocolo", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(default=10)

    chequeo_id = fields.Many2one(
        "mc.rov.chequeo", string="Chequeo", required=True, ondelete="restrict"
    )
    seccion = fields.Selection(related="chequeo_id.seccion", string="Sección", store=True)

    componente_id = fields.Many2one("mc.rov.componente", string="Componente", ondelete="restrict")

    resultado = fields.Selection(RESULTADOS_CHEQUEO, string="Resultado")
    detalle = fields.Char(string="Detalle")


class McRovProtocoloHallazgo(models.Model):
    """Lo que se encontró, estructurado.

    Reusa `mc.rov.componente` y `mc.rov.subtipo`, los mismos catálogos que usan las líneas
    de trabajo. Eso es lo que permite correlacionar: *dónde* se encuentran los hallazgos y
    *dónde* se hacen los trabajos hablan el mismo idioma.

    `detalle` sigue existiendo pero como complemento del hallazgo, nunca en su lugar. Sin la
    parte estructurada el técnico escribe "se vio raro el motor" y no hay nada que agregar.
    """

    _name = "mc.rov.protocolo.hallazgo"
    _description = "Hallazgo registrado en un protocolo"
    _order = "protocolo_id, sequence, id"

    protocolo_id = fields.Many2one(
        "mc.rov.protocolo", string="Protocolo", required=True, ondelete="cascade", index=True
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
    # hallazgo lo reveló un chequeo del protocolo o si alguien lo vio de casualidad. De ahí
    # sale el resultado más útil de todos — un hallazgo frecuente que ningún chequeo detecta
    # es un chequeo que falta.
    chequeo_origen_id = fields.Many2one(
        "mc.rov.protocolo.chequeo",
        string="Detectado por",
        ondelete="set null",
        help="El chequeo que lo destapó, si fue uno. Vacío significa que se encontró por "
        "fuera del checklist.",
    )

    detalle = fields.Text(string="Detalle")

    lot_id = fields.Many2one(related="protocolo_id.lot_id", string="Equipo", store=True)
