from odoo import models, fields, api

class StockLot(models.Model):
    _inherit = 'stock.lot'

    repair_count = fields.Integer(
        string='Reparaciones',
        compute='_compute_repair_count'
    )

    ultima_mantencion = fields.Date(
        string='Última mantención',
        compute='_compute_ultima_mantencion',
        store=False
    )

    @api.depends()
    def _compute_repair_count(self):
        for lot in self:
            lot.repair_count = self.env['repair.order'].search_count([
                ('lot_id', '=', lot.id),
                ('state', '=', 'done')
            ])

    @api.depends()
    def _compute_ultima_mantencion(self):
        for lot in self:
            ultima = self.env['repair.order'].search([
                ('lot_id', '=', lot.id),
                ('state', '=', 'done')
            ], order='id desc', limit=1)
            lot.ultima_mantencion = ultima.create_date.date() if ultima else False

    def action_ver_reparaciones(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reparaciones',
            'res_model': 'repair.order',
            'view_mode': 'list,form',
            'domain': [('lot_id', '=', self.id)],
            'context': {'default_lot_id': self.id},
        }