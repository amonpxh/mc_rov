"""Salida y devolución por movimientos efectivos, sin repetir unidades fabricadas."""

from odoo import fields, models

from .production_kpi_event import append_event, lock_source, unit_design


class ProductionMilestoneStock(models.Model):
    """Una transferencia interna no cumple una entrega al cliente."""

    _inherit = "stock.move"

    def _action_done(self, cancel_backorder=False):
        result = super()._action_done(cancel_backorder=cancel_backorder)
        for move in result:
            outward = (
                move.location_id.usage == "internal" and move.location_dest_id.usage == "customer"
            )
            returned = (
                move.location_id.usage == "customer" and move.location_dest_id.usage == "internal"
            )
            if move.state != "done" or not (outward or returned):
                continue
            for line in move.move_line_ids.filtered(lambda row: row.lot_id and row.quantity > 0):
                lot = line.lot_id
                if not lot.es_un_rov:
                    continue
                lock_source(lot, access="read")
                made = (
                    self.env["mc.rov.production.event"]
                    .sudo()
                    .search(
                        [
                            ("kind", "=", "manufactured"),
                            ("company_id", "=", move.company_id.id),
                            ("lot_id", "=", lot.id),
                        ]
                    )
                )
                if len(made) != 1:
                    continue
                append_event(
                    move,
                    lot,
                    "outbound" if outward else "reversed",
                    made.identity if outward else f"move:{move.id}:lot:{lot.id}",
                    {
                        "unit_identity": made.identity,
                        "reversal_of": "outbound" if returned else False,
                        "customer_id": move.partner_id.id,
                        **unit_design(move, lot, move.company_id),
                    },
                    at=move.date or fields.Datetime.now(),
                    production_id=made.production_id.id,
                    move_id=move.id,
                )
                if outward:
                    append_event(
                        move,
                        lot,
                        "unit_movement",
                        f"move:{move.id}:lot:{lot.id}",
                        {
                            "unit_identity": made.identity,
                            "effect": "outbound",
                            **unit_design(move, lot, move.company_id),
                        },
                        at=move.date or fields.Datetime.now(),
                        production_id=made.production_id.id,
                        move_id=move.id,
                    )
        return result


class ProductionUnbuildCapture(models.Model):
    """El desmontaje modifica saldo vigente y conserva fabricación histórica."""

    _inherit = "mrp.unbuild"

    def action_unbuild(self):
        lock_source(self)
        result = super().action_unbuild()
        for unbuild in self.filtered(lambda row: row.state == "done" and row.lot_id.es_un_rov):
            lot = unbuild.lot_id
            lock_source(lot, access="read")
            made = (
                self.env["mc.rov.production.event"]
                .sudo()
                .search(
                    [
                        ("kind", "=", "manufactured"),
                        ("lot_id", "=", lot.id),
                        ("company_id", "=", unbuild.company_id.id),
                    ]
                )
            )
            if len(made) == 1:
                append_event(
                    unbuild,
                    lot,
                    "reversed",
                    f"unbuild:{unbuild.id}:lot:{lot.id}",
                    {
                        "unit_identity": made.identity,
                        "reversal_of": "manufactured",
                        "unbuild_id": unbuild.id,
                        **unit_design(unbuild, lot, unbuild.company_id),
                    },
                    at=fields.Datetime.now(),
                    production_id=made.production_id.id,
                )
        return result
