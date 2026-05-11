from odoo import models, fields

class RepairOrder(models.Model):
    _inherit = 'repair.order'

    # Tipo de intervención
    tipo_intervencion = fields.Selection([
        ('diagnostico', 'Diagnóstico'),
        ('reparacion_correctiva', 'Reparación correctiva'),
        ('mantencion_preventiva', 'Mantención preventiva'),
        ('conversion', 'Conversión / Upgrade'),
    ], string='Tipo de intervención')

    # Ítems del sistema
    item_2 = fields.Char(string='Ítem 2')
    item_3 = fields.Char(string='Ítem 3')
    item_4 = fields.Char(string='Ítem 4')
    item_5 = fields.Char(string='Ítem 5')

    # Diagnóstico
    falla_reportada = fields.Text(string='Falla reportada por cliente')

    # Líneas de falla
    linea_falla_ids = fields.One2many('mc.rov.linea.falla', 'repair_id', string='Trabajos realizados')

    # Resultado
    estado_final = fields.Selection([
        ('reparado', 'Reparado'),
        ('no_reparado', 'No reparado'),
        ('derivado', 'Derivado a fabricante'),
        ('pendiente_repuesto', 'Pendiente repuesto'),
    ], string='Estado final')

    causa_raiz = fields.Selection([
        ('mal_uso', 'Mal uso'),
        ('desgaste', 'Desgaste normal'),
        ('accidente', 'Accidente'),
        ('falla_fabricacion', 'Falla de fabricación'),
        ('corrosion', 'Corrosión'),
        ('desconocida', 'Desconocida'),
    ], string='Causa raíz')

    garantia_reparacion = fields.Boolean(string='Garantía de reparación')
    fecha_garantia = fields.Date(string='Vencimiento garantía')
    fecha_entrega_real = fields.Date(string='Fecha de entrega real')
    observaciones_salida = fields.Text(string='Observaciones de salida')