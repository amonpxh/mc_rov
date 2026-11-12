"""Captura cierres y unidades solo después de sus acciones nativas completas."""

from odoo import fields, models

from .production_kpi_event import append_event, lock_source, unit_design


class RepairProductionCapture(models.Model):
    """El primer cierre técnico es distinto de la fecha declarada y del despacho."""

    _inherit = "repair.order"

    def action_repair_done(self):
        lock_source(self)
        pending = self.filtered(lambda row: row.state != "done" or not row.lot_id.es_un_rov)
        if not pending:
            return True
        # Un reintento RPC sobre un cierre ya completado no debe ejecutar otra vez
        # el movimiento nativo. Una reapertura real sí pasa por la acción normal.
        result = super(RepairProductionCapture, pending).action_repair_done()
        for order in pending:
            move = order.move_id
            if order.state != "done" or not order.lot_id.es_un_rov or move.state != "done":
                continue
            if not any(
                line.lot_id == order.lot_id and line.quantity > 0 for line in move.move_line_ids
            ):
                continue
            append_event(
                order,
                order.lot_id,
                "repair_done",
                f"repair:{order.id}",
                {
                    "customer_id": order.partner_id.id,
                    "customer_label": order.partner_id.display_name or False,
                    "intervention_ids": order.tipo_intervencion_ids.ids,
                    "repair": any(order.tipo_intervencion_ids.mapped("es_reparacion")),
                    "maintenance": any(order.tipo_intervencion_ids.mapped("es_mantencion")),
                    "warranty": (
                        order.under_warranty if "under_warranty" in order._fields else False
                    ),
                    **unit_design(order, order.lot_id, order.company_id),
                },
                at=fields.Datetime.now(),
                repair_id=order.id,
                move_id=move.id,
            )
        return result


class ManufacturingProductionCapture(models.Model):
    """Una salida serializada acredita unidades; no basta marcar una MO realizada."""

    _inherit = "mrp.production"

    def button_mark_done(self):
        lock_source(self)
        previous = {production.id: production.state for production in self}
        result = super().button_mark_done()
        service = self.env["mc.rov.acceptance.activity.automation"]
        for production in self.filtered(
            lambda row: row.state == "done" and previous[row.id] != "done"
        ):
            for lot in service._produced_lots(production).filtered("es_un_rov"):
                design = dict(production.mc_design_snapshot or {})
                if design.get("bom_id") and (
                    design["bom_id"] != production.bom_id.id
                    or design.get("bom_version") != production.bom_id.version
                ):
                    design.update(revision_key=False, revision_label=False, design_conflict=True)
                append_event(
                    production,
                    lot,
                    "manufactured",
                    f"group:{production.production_group_id.id}:lot:{lot.id}",
                    {"production_group_id": production.production_group_id.id, **design},
                    at=fields.Datetime.now(),
                    production_id=production.id,
                )
        return result
