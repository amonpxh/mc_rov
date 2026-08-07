import logging

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

# Largo del ciclo de mantención. Vive en un parámetro de sistema para que se pueda
# ajustar sin desplegar; la constante es solo el valor por defecto.
CICLO_MANTENCION_PARAM = "mc_rov.meses_ciclo_mantencion"
CICLO_MANTENCION_MESES = 12

# Raíz del árbol de categorías que define qué producto es un vehículo ROV.
# El parámetro de sistema manda: permite reorganizar el árbol sin desplegar código.
# El XML ID es el que dejó la importación original del árbol y solo actúa como respaldo
# si el parámetro nunca se sembró (ver migrations/19.0.2.0.0/post-migrate.py).
ROV_CATEG_PARAM = "mc_rov.rov_category_id"
ROV_CATEG_XMLID_MODULE = "__import__"
ROV_CATEG_XMLID_NAME = "cat_ROV"


class StockLot(models.Model):
    """Extensión de stock.lot para seguimiento de reparaciones ROV y ficha técnica del equipo.

    Centraliza en el número de serie toda la información técnica que antes vivía
    en campos x_studio_* creados por Studio, haciéndola parte del módulo versionado.
    """

    _inherit = "stock.lot"

    es_un_rov = fields.Boolean(
        string="Es un ROV",
        compute="_compute_es_un_rov",
        store=True,
        help="Se deriva de la categoría del producto: se enciende cuando pertenece a la "
        "rama de vehículos ROV. No es editable — para cambiarlo, recategorice el producto.",
    )

    def _get_rov_root_category(self):
        """Resuelve la categoría raíz de vehículos ROV.

        Devuelve un recordset vacío si no resuelve, en vez de lanzar excepción: este
        método corre en cada creación de número de serie (incluidas las de órdenes de
        fabricación) y hacerlo fallar dejaría inaccesible toda la vista de lotes.
        """
        categories = self.env["product.category"]

        raw = self.env["ir.config_parameter"].sudo().get_param(ROV_CATEG_PARAM)
        if raw:
            try:
                categ = categories.browse(int(raw)).exists()
            except (TypeError, ValueError):
                # Parámetro con basura: se avisa y se cae al respaldo, no se propaga
                _logger.warning(
                    "%s tiene un valor no numérico (%r); se ignora.", ROV_CATEG_PARAM, raw
                )
            else:
                if categ:
                    return categ

        # El XML ID lo generó una importación, no este módulo. Se busca filtrando por
        # modelo en vez de usar env.ref: si ese ID externo apuntara a otro modelo, el
        # child_of operaría en silencio sobre la categoría equivocada.
        imd = (
            self.env["ir.model.data"]
            .sudo()
            .search(
                [
                    ("module", "=", ROV_CATEG_XMLID_MODULE),
                    ("name", "=", ROV_CATEG_XMLID_NAME),
                    ("model", "=", "product.category"),
                ],
                limit=1,
            )
        )
        if imd:
            return categories.browse(imd.res_id).exists()

        return categories

    @api.depends("product_id.categ_id")
    def _compute_es_un_rov(self):
        """Un lote es ROV si la categoría de su producto cuelga de la raíz de vehículos.

        La búsqueda de categorías se hace una vez por recordset, no por lote, porque el
        ORM llama a este compute en lotes durante importaciones y recálculos masivos.
        """
        root = self._get_rov_root_category()
        if root:
            rov_categs = self.env["product.category"].search([("id", "child_of", root.id)])
        else:
            # Sin raíz no hay forma de decidir. Se apaga todo, que es destructivo:
            # se registra como error para que quede en el log del servidor.
            _logger.error(
                "No se pudo resolver la categoría raíz de ROV (parámetro %s ni XML ID %s.%s). "
                "Todos los números de serie quedarán marcados como no-ROV.",
                ROV_CATEG_PARAM,
                ROV_CATEG_XMLID_MODULE,
                ROV_CATEG_XMLID_NAME,
            )
            rov_categs = self.env["product.category"]

        for lot in self:
            lot.es_un_rov = lot.product_id.categ_id in rov_categs

    # --- Estado ---

    mc_estado_comercial = fields.Selection(
        [
            ("Disponible", "Disponible"),
            ("En arriendo", "En arriendo"),
            ("Vendido", "Vendido"),
            ("Baja", "Baja"),
        ],
        string="Estado Comercial",
        help="Indica en qué estado se encuentra el equipo (ej. el equipo está siendo arrendado).",
    )

    # Inversa de repair.order.lot_id. Existe para que mc_estado_operativo pueda ser un
    # computed almacenado: sin la relación, el ORM no sabe cuándo recalcularlo.
    repair_ids = fields.One2many(
        "repair.order",
        "lot_id",
        string="Órdenes de reparación",
    )

    mc_estado_operativo = fields.Selection(
        [
            ("Operativo", "Operativo"),
            ("En mantención", "En mantención"),
            ("En reparación", "En reparación"),
        ],
        string="Estado Operativo",
        compute="_compute_mc_estado_operativo",
        store=True,
        help="Se deriva de las órdenes de reparación abiertas del equipo. No es editable: "
        "para cambiarlo, abra o cierre la orden correspondiente.",
    )

    @api.depends("repair_ids.state", "repair_ids.tipo_intervencion_ids.es_mantencion")
    def _compute_mc_estado_operativo(self):
        """El estado del equipo es el de sus órdenes abiertas, no un dato aparte.

        Mantenerlo a mano creaba dos fuentes de verdad: el técnico abría la orden y el
        número de serie seguía diciendo "Operativo" con el equipo desarmado en el banco.

        Los borradores no cuentan, igual que en mc_repair_count y ultima_mantencion: una
        orden en draft es una cotización, el equipo todavía no entró al taller.
        """
        for lot in self:
            abiertas = lot.repair_ids.filtered(
                lambda order: order.state not in ("draft", "done", "cancel")
            )
            if not abiertas:
                lot.mc_estado_operativo = "Operativo"
            elif any(abiertas.mapped("tipo_intervencion_ids.es_mantencion")):
                lot.mc_estado_operativo = "En mantención"
            else:
                lot.mc_estado_operativo = "En reparación"

    # --- Especificaciones ---

    mc_chasis = fields.Selection(
        [
            ("Plástico", "Plástico"),
            ("Inox", "Inox"),
        ],
        string="Chasis",
    )

    mc_modelo_motores = fields.Selection(
        [
            ("T200", "T200"),
            ("T200 & T500", "T200 y T500"),
            ("T500", "T500"),
            ("W170", "W170"),
            ("DWT8537", "DWT8537"),
        ],
        string="Modelo motores",
    )

    mc_n_motores = fields.Integer(string="N° motores")

    mc_posicion_motores = fields.Selection(
        [
            ("Recto", "Recto"),
            ("Vectorial", "Vectorial"),
        ],
        string="Posición motores",
    )

    mc_peso_consola = fields.Float(string="Peso Consola")
    mc_peso_rov = fields.Float(string="Peso ROV")

    mc_sensor_presion = fields.Selection(
        [
            ("30 bar", "30 bar (300 m)"),
            ("100 bar (1000m)", "100 bar (1000m)"),
        ],
        string="Sensor de presión",
    )

    mc_tarjeta_comunicacion_rov = fields.Selection(
        [
            ("V50", "V50"),
            ("V30", "V30"),
        ],
        string="Tarjeta de comunicación ROV",
    )

    mc_tarjeta_comunicacion_consola = fields.Selection(
        [
            ("V50", "V50"),
            ("V30", "V30"),
        ],
        string="Tarjeta de comunicación Consola",
    )

    mc_version_qground = fields.Char(string="Versión QGround")

    mc_controlador_vuelo = fields.Selection(
        [
            ("Navigator", "Navigator"),
            ("Pixhawk", "Pixhawk"),
        ],
        string="Controlador de Vuelo",
    )

    mc_version_px4 = fields.Char(string="Versión PX4")
    mc_version_navigator = fields.Char(string="Versión Navigator")
    mc_version_ardusub = fields.Char(string="Versión Ardusub")

    # --- Periféricos ---

    mc_salida_brazo = fields.Boolean(string="Salida de brazo")
    mc_brazo = fields.Char(string="Brazo")
    mc_cantidad_luces = fields.Integer(string="Cantidad de luces")
    mc_dispositivos_extra = fields.Char(string="Dispositivos extra")

    # --- Umbilical ---

    mc_n_serie_umbilical = fields.Char(string="N° serie de Umbilical")
    mc_longitud = fields.Float(string="Longitud")
    mc_diametro = fields.Float(string="Diámetro")
    mc_peso_umbilical = fields.Float(string="Peso Umbilical")
    mc_modelo_fuente = fields.Char(string="Modelo de fuente")

    mc_fuente_energia = fields.Selection(
        [
            ("UPS", "UPS"),
            ("Generador", "Generador"),
            ("Transformador", "Transformador"),
        ],
        string="Fuente de energía",
    )

    mc_tension_salida = fields.Integer(string="Tensión de salida")
    mc_consumo_corriente = fields.Char(string="Consumo corriente")
    mc_en_reposo = fields.Integer(string="En reposo")
    mc_esfuerzo = fields.Integer(string="Esfuerzo")
    mc_limitacion_pilot_gain = fields.Integer(string="Limitación pilot gain")
    mc_ganancia_luz = fields.Integer(string="Ganancia Luz")
    mc_tiempo_prueba_lab = fields.Float(string="Tiempo de Prueba")
    mc_prueba_leak = fields.Boolean(string="Prueba de leak")
    # Valor calculado externamente (ej. medición de red); se edita solo desde herramientas técnicas
    mc_ancho_banda = fields.Char(string="Ancho de banda (puede variar ±5%)")
    mc_subida = fields.Float(string="Subida")
    mc_bajada = fields.Float(string="Bajada")
    mc_temperatura_interior_lab = fields.Float(string="Temperatura interior")
    mc_temperatura_exterior_lab = fields.Float(string="Temperatura exterior")

    # --- Prueba en Terreno ---

    mc_fecha_prueba = fields.Date(string="Fecha")
    mc_lugar = fields.Char(string="Lugar")
    mc_profundidad = fields.Integer(string="Profundidad")
    mc_velocidad_corriente = fields.Float(string="Velocidad de la corriente")

    mc_alimentacion = fields.Selection(
        [
            ("Transformador", "Transformador"),
            ("Generador", "Generador"),
            ("UPS", "UPS"),
        ],
        string="Alimentación",
    )

    mc_tiempo_prueba_terreno = fields.Float(string="Tiempo de prueba")
    mc_temperatura_interior_terreno = fields.Float(string="Temperatura interior (Prueba)")
    mc_temperatura_exterior_terreno = fields.Float(string="Temperatura exterior (Prueba)")
    mc_observacion = fields.Text(string="Observación")

    # --- Reparaciones ---

    # Reparaciones y mantenciones se cuentan por separado: mezclarlas hacía que el botón
    # "Reparaciones" dijera 5 cuando eran 3 reparaciones y 2 mantenciones.
    mc_repair_count = fields.Integer(
        string="Reparaciones",
        compute="_compute_mc_contadores",
    )

    mc_mantencion_count = fields.Integer(
        string="Mantenciones",
        compute="_compute_mc_contadores",
    )

    # Almacenados para que proxima_mantencion pueda serlo y la vista de vencidos filtre
    # por ella. La relación repair_ids es lo que permite al ORM saber cuándo recalcular.
    ultima_mantencion = fields.Date(
        string="Última mantención",
        compute="_compute_ultimas_fechas",
        store=True,
        help="Última mantención cerrada. Las reparaciones correctivas no cuentan: un "
        "equipo reparado en marzo sigue debiendo su mantención anual.",
    )

    ultima_reparacion = fields.Date(
        string="Última reparación",
        compute="_compute_ultimas_fechas",
        store=True,
        help="Última reparación cerrada, según los tipos marcados como reparación en el "
        "catálogo de tipos de intervención.",
    )

    # --- Ciclo de mantención ---

    mc_fecha_puesta_servicio = fields.Date(
        string="Puesta en servicio",
        help="Entrega al cliente si el equipo se vendió, o primera disponibilidad de "
        "arriendo si es de flota. Arranca el ciclo de mantención. Se carga a mano: los "
        "equipos entregados antes de que existiera Odoo no tienen movimiento de stock "
        "del que derivarla.",
    )

    proxima_mantencion = fields.Date(
        string="Próxima mantención",
        compute="_compute_proxima_mantencion",
        store=True,
        help="Se calcula sumando el ciclo configurado a la última mantención, o a la "
        "puesta en servicio si el equipo nunca ha tenido una.",
    )

    def _ultima_fecha_entrega(self, lot, marca):
        """Fecha de entrega de la última orden cerrada de `lot` cuyo tipo lleve `marca`.

        `marca` es el nombre del booleano del catálogo (es_mantencion o es_reparacion).
        Se lee la marca en vez de comparar nombres de tipo para que agregar un tipo
        nuevo sea marcar una casilla y no editar este método.

        Ordena por fecha y no por id porque las órdenes no se cierran en el orden en que
        se crean. Se excluyen las que no tienen fecha: en PostgreSQL un DESC pone los
        NULL primero y habrían ganado el limit=1.
        """
        ultima = self.env["repair.order"].search(
            [
                ("lot_id", "=", lot.id),
                ("state", "=", "done"),
                (f"tipo_intervencion_ids.{marca}", "=", True),
                ("fecha_entrega_real", "!=", False),
            ],
            order="fecha_entrega_real desc, id desc",
            limit=1,
        )
        return ultima.fecha_entrega_real if ultima else False

    @api.depends()
    def _compute_mc_contadores(self):
        Repair = self.env["repair.order"]
        for lot in self:
            base = [("lot_id", "=", lot.id), ("state", "=", "done")]
            lot.mc_repair_count = Repair.search_count(
                base + [("tipo_intervencion_ids.es_reparacion", "=", True)]
            )
            lot.mc_mantencion_count = Repair.search_count(
                base + [("tipo_intervencion_ids.es_mantencion", "=", True)]
            )

    @api.depends(
        "repair_ids.state",
        "repair_ids.fecha_entrega_real",
        "repair_ids.tipo_intervencion_ids.es_mantencion",
        "repair_ids.tipo_intervencion_ids.es_reparacion",
    )
    def _compute_ultimas_fechas(self):
        for lot in self:
            lot.ultima_mantencion = self._ultima_fecha_entrega(lot, "es_mantencion")
            lot.ultima_reparacion = self._ultima_fecha_entrega(lot, "es_reparacion")

    @api.depends("ultima_mantencion", "mc_fecha_puesta_servicio")
    def _compute_proxima_mantencion(self):
        """Cuenta el ciclo desde la última mantención, o desde la puesta en servicio.

        Un equipo al que se le hizo mantención a los 18 meses reinicia el contador ahí,
        no en el aniversario teórico: lo que importa es cuándo se intervino de verdad.

        Sin puesta en servicio no hay reloj. Es deliberado: mientras el equipo no salga
        a terreno no tiene sentido reclamarle mantención, y así los que están en bodega
        no ensucian la lista de vencidos.
        """
        meses = self._meses_ciclo_mantencion()
        for lot in self:
            partida = lot.ultima_mantencion or lot.mc_fecha_puesta_servicio
            lot.proxima_mantencion = partida + relativedelta(months=meses) if partida else False

    def _meses_ciclo_mantencion(self):
        """Largo del ciclo en meses, configurable sin desplegar.

        Vive en un parámetro de sistema por si algún día distinguen equipos de uso
        intensivo. Un valor corrupto no debe romper la ficha de todos los equipos, así
        que cae al default avisando en el log.
        """
        raw = self.env["ir.config_parameter"].sudo().get_param(CICLO_MANTENCION_PARAM)
        if not raw:
            return CICLO_MANTENCION_MESES
        try:
            return int(raw)
        except (TypeError, ValueError):
            _logger.warning(
                "%s tiene un valor no numérico (%r); se usan %s meses.",
                CICLO_MANTENCION_PARAM,
                raw,
                CICLO_MANTENCION_MESES,
            )
            return CICLO_MANTENCION_MESES

    def action_ver_reparaciones(self):
        """Abre la lista de órdenes de reparación filtradas por este número de serie."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Reparaciones",
            "res_model": "repair.order",
            "view_mode": "list,form",
            "domain": [("lot_id", "=", self.id)],
            "context": {"default_lot_id": self.id},
        }
