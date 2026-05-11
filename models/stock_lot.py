from odoo import models, fields, api


class StockLot(models.Model):
    """Extensión de stock.lot para seguimiento de historial de reparaciones por ROV.

    Cada número de serie (lote) de un equipo ROV puede consultarse directamente
    desde el formulario del lote para ver cuántas reparaciones tiene y cuándo
    fue la última mantención registrada.
    """

    _inherit = 'stock.lot'

    es_un_rov = fields.Boolean(
        string='Es un ROV',
        help='Marca este número de serie como equipo ROV para mostrar historial de mantenciones.',
    )

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
