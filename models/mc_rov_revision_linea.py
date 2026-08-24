"""Las tres líneas de una revisión: el checklist, los hallazgos y la inspección de sellos.

Salen de `mc_rov_revision.py` en 19.0.21.0.0, y el motivo es de tamaño y no de diseño: ese
archivo pasó de 1400 líneas, que es el techo escrito en `.pylintrc`. **Subir el techo otra vez
era el camino fácil y el equivocado** — el largo de aquel archivo lo produce la convención de
explicar el porqué en el código, pero estas tres clases son modelos aparte y ya estaban al
final, sin nada que las atara a la cabecera salvo la costumbre.

Las tres cuelgan de la revisión con `ondelete="cascade"`: no existen sin ella.
"""

from odoo import models, fields, api

from .mc_rov_revision import ESTADOS_SELLO, RESULTADOS_CHEQUEO, SEVERIDADES


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
