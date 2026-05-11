from odoo import models, fields, api


class StockLot(models.Model):
    """Extensión de stock.lot para seguimiento de reparaciones ROV y ficha técnica del equipo.

    Centraliza en el número de serie toda la información técnica que antes vivía
    en campos x_studio_* creados por Studio, haciéndola parte del módulo versionado.
    """

    _inherit = 'stock.lot'

    es_un_rov = fields.Boolean(
        string='Es un ROV',
        help='Marca este número de serie como equipo ROV para mostrar historial de mantenciones.',
    )

    # --- Estado ---

    estado_comercial = fields.Selection([
        ('Disponible', 'Disponible'),
        ('En arriendo', 'En arriendo'),
        ('Vendido', 'Vendido'),
        ('Baja', 'Baja'),
    ], string='Estado Comercial',
        help='Indica en qué estado se encuentra el equipo (ej. el equipo está siendo arrendado).')

    estado_operativo = fields.Selection([
        ('Operativo', 'Operativo'),
        ('En mantención', 'En mantención'),
        ('En reparación', 'En reparación'),
    ], string='Estado Operativo',
        help='Indica si el equipo está siendo reparado, en mantención o está operativo.')

    # --- Especificaciones ---

    chasis = fields.Selection([
        ('Plástico', 'Plástico'),
        ('Inox', 'Inox'),
    ], string='Chasis')

    modelo_motores = fields.Selection([
        ('T200', 'T200'),
        ('T200 & T500', 'T200 y T500'),
        ('T500', 'T500'),
        ('W170', 'W170'),
        ('DWT8537', 'DWT8537'),
    ], string='Modelo motores')

    n_motores = fields.Integer(string='N° motores')

    posicion_motores = fields.Selection([
        ('Recto', 'Recto'),
        ('Vectorial', 'Vectorial'),
    ], string='Posición motores')

    peso_consola = fields.Float(string='Peso Consola')
    peso_rov = fields.Float(string='Peso ROV')

    sensor_presion = fields.Selection([
        ('30 bar', '30 bar (300 m)'),
        ('100 bar (1000m)', '100 bar (1000m)'),
    ], string='Sensor de presión')

    tarjeta_comunicacion_rov = fields.Selection([
        ('V50', 'V50'),
        ('V30', 'V30'),
    ], string='Tarjeta de comunicación ROV')

    tarjeta_comunicacion_consola = fields.Selection([
        ('V50', 'V50'),
        ('V30', 'V30'),
    ], string='Tarjeta de comunicación Consola')

    version_qground = fields.Char(string='Versión QGround')

    controlador_vuelo = fields.Selection([
        ('Navigator', 'Navigator'),
        ('Pixhawk', 'Pixhawk'),
    ], string='Controlador de Vuelo')

    version_px4 = fields.Char(string='Versión PX4')
    version_navigator = fields.Char(string='Versión Navigator')
    version_ardusub = fields.Char(string='Versión Ardusub')

    # --- Periféricos ---

    salida_brazo = fields.Boolean(string='Salida de brazo')
    brazo = fields.Char(string='Brazo')
    cantidad_luces = fields.Integer(string='Cantidad de luces')
    dispositivos_extra = fields.Char(string='Dispositivos extra')

    # --- Umbilical ---

    n_serie_umbilical = fields.Char(string='N° serie de Umbilical')
    longitud = fields.Float(string='Longitud')
    diametro = fields.Float(string='Diámetro')
    peso_umbilical = fields.Float(string='Peso Umbilical')
    modelo_fuente = fields.Char(string='Modelo de fuente')

    fuente_energia = fields.Selection([
        ('UPS', 'UPS'),
        ('Generador', 'Generador'),
        ('Transformador', 'Transformador'),
    ], string='Fuente de energía')

    tension_salida = fields.Integer(string='Tensión de salida')
    consumo_corriente = fields.Char(string='Consumo corriente')
    en_reposo = fields.Integer(string='En reposo')
    esfuerzo = fields.Integer(string='Esfuerzo')
    limitacion_pilot_gain = fields.Integer(string='Limitación pilot gain')
    ganancia_luz = fields.Integer(string='Ganancia Luz')
    tiempo_prueba_lab = fields.Float(string='Tiempo de Prueba')
    prueba_leak = fields.Boolean(string='Prueba de leak')
    # Valor calculado externamente (ej. medición de red); se edita solo desde herramientas técnicas
    ancho_banda = fields.Char(string='Ancho de banda (puede variar ±5%)')
    subida = fields.Float(string='Subida')
    bajada = fields.Float(string='Bajada')
    temperatura_interior_lab = fields.Float(string='Temperatura interior')
    temperatura_exterior_lab = fields.Float(string='Temperatura exterior')

    # --- Prueba en Terreno ---

    fecha_prueba = fields.Date(string='Fecha')
    lugar = fields.Char(string='Lugar')
    profundidad = fields.Integer(string='Profundidad')
    velocidad_corriente = fields.Float(string='Velocidad de la corriente')

    alimentacion = fields.Selection([
        ('Transformador', 'Transformador'),
        ('Generador', 'Generador'),
        ('UPS', 'UPS'),
    ], string='Alimentación')

    tiempo_prueba_terreno = fields.Float(string='Tiempo de prueba')
    temperatura_interior_terreno = fields.Float(string='Temperatura interior (Prueba)')
    temperatura_exterior_terreno = fields.Float(string='Temperatura exterior (Prueba)')
    observacion = fields.Text(string='Observación')

    # --- Reparaciones ---

    # Cantidad de órdenes de reparación completadas para este número de serie
    repair_count = fields.Integer(
        string='Reparaciones',
        compute='_compute_repair_count',
    )

    # Fecha de la última orden completada — usa create_date como aproximación hasta
    # que repair.order tenga un campo de fecha real de cierre (pendiente)
    ultima_mantencion = fields.Date(
        string='Última mantención',
        compute='_compute_ultima_mantencion',
        store=False,
    )

    @api.depends()
    def _compute_repair_count(self):
        for lot in self:
            lot.repair_count = self.env['repair.order'].search_count([
                ('lot_id', '=', lot.id),
                ('state', '=', 'done'),
            ])

    @api.depends()
    def _compute_ultima_mantencion(self):
        for lot in self:
            ultima = self.env['repair.order'].search([
                ('lot_id', '=', lot.id),
                ('state', '=', 'done'),
            ], order='id desc', limit=1)
            lot.ultima_mantencion = ultima.create_date.date() if ultima else False

    def action_ver_reparaciones(self):
        """Abre la lista de órdenes de reparación filtradas por este número de serie."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reparaciones',
            'res_model': 'repair.order',
            'view_mode': 'list,form',
            'domain': [('lot_id', '=', self.id)],
            'context': {'default_lot_id': self.id},
        }
