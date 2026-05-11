from odoo import models, fields


class McRovComponente(models.Model):
    """Catálogo maestro de componentes ROV.

    Agrupa los componentes físicos y de software que pueden fallar o
    intervenirse en una orden de reparación (motor, umbilical, cámara, etc.).
    Cada componente puede tener uno o varios subtipos para mayor precisión
    en el registro de trabajos realizados.
    """

    _name = 'mc.rov.componente'
    _description = 'Componente ROV'
    _order = 'name'

    name = fields.Char(string='Componente', required=True)
    # Subtipos gestionados desde el formulario del componente (inline)
    subtipo_ids = fields.One2many('mc.rov.subtipo', 'componente_id', string='Subtipos')
    active = fields.Boolean(default=True)


class McRovSubtipo(models.Model):
    """Subtipo de un componente ROV.

    Permite detallar qué parte específica del componente fue intervenida.
    Por ejemplo, dentro de 'Motor' puede ser 'Rotor', 'Hélice' o 'ESC'.
    El dominio en mc.rov.linea.falla filtra los subtipos según el componente
    seleccionado en cada línea.
    """

    _name = 'mc.rov.subtipo'
    _description = 'Subtipo de componente ROV'
    _order = 'componente_id, name'

    name = fields.Char(string='Subtipo', required=True)
    componente_id = fields.Many2one(
        'mc.rov.componente',
        string='Componente',
        required=True,
        ondelete='cascade',
    )
    active = fields.Boolean(default=True)


class McRovLineaFalla(models.Model):
    """Línea de trabajo registrada en una orden de reparación.

    Cada línea describe una intervención específica: qué componente se trató,
    qué subtipo exacto, qué acción se tomó y un detalle libre. Una orden puede
    tener múltiples líneas si se intervinieron varios componentes.
    """

    _name = 'mc.rov.linea.falla'
    _description = 'Línea de falla en orden de reparación'
    _order = 'sequence'

    sequence = fields.Integer(default=10)
    repair_id = fields.Many2one(
        'repair.order',
        string='Orden de reparación',
        required=True,
        ondelete='cascade',
    )
    componente_id = fields.Many2one('mc.rov.componente', string='Componente', required=True)
    # El dominio se evalúa por fila en el one2many editable (soportado desde Odoo 17+)
    subtipo_id = fields.Many2one(
        'mc.rov.subtipo',
        string='Subtipo',
        domain="[('componente_id', '=', componente_id)]",
    )
    accion = fields.Selection([
        ('cambio_completo', 'Cambio completo'),
        ('cambio_componente', 'Cambio de componente'),
        ('reparacion', 'Reparación'),
        ('mantencion_preventiva', 'Mantención preventiva'),
        ('limpieza', 'Limpieza'),
        ('calibracion', 'Calibración'),
        ('configuracion', 'Configuración / Software'),
        ('soldadura', 'Soldadura'),
        ('sin_solucion', 'Sin solución'),
        ('derivado', 'Derivado a fabricante'),
    ], string='Acción', required=True)
    detalle = fields.Text(string='Detalle')
