from odoo import models, fields

class McRovComponente(models.Model):
    _name = 'mc.rov.componente'
    _description = 'Componente ROV'
    _order = 'name'

    name = fields.Char(string='Componente', required=True)
    subtipo_ids = fields.One2many('mc.rov.subtipo', 'componente_id', string='Subtipos')
    active = fields.Boolean(default=True)


class McRovSubtipo(models.Model):
    _name = 'mc.rov.subtipo'
    _description = 'Subtipo de componente ROV'
    _order = 'componente_id, name'

    name = fields.Char(string='Subtipo', required=True)
    componente_id = fields.Many2one('mc.rov.componente', string='Componente', required=True, ondelete='cascade')
    active = fields.Boolean(default=True)


class McRovLineaFalla(models.Model):
    _name = 'mc.rov.linea.falla'
    _description = 'Línea de falla en orden de reparación'
    _order = 'sequence'

    sequence = fields.Integer(default=10)
    repair_id = fields.Many2one('repair.order', string='Orden de reparación', required=True, ondelete='cascade')
    componente_id = fields.Many2one('mc.rov.componente', string='Componente', required=True)
    subtipo_id = fields.Many2one(
        'mc.rov.subtipo',
        string='Subtipo',
        domain="[('componente_id', '=', componente_id)]"
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