"""Evidencia de la llegada física de la unidad de una visita de reparación."""

# pylint: disable=unknown-option-value
from odoo import _, api, fields, models
from odoo.exceptions import AccessError


_ARRIVAL_CAPTURE = object()


class RepairArrival(models.Model):
    """Sella la llegada y la fecha nativa que respaldó el registro."""

    _name = "mc.rov.repair.arrival"
    _description = "Recepción acreditada de una visita ROV"
    _check_company_auto = True

    repair_id = fields.Many2one(
        "repair.order", required=True, ondelete="restrict", check_company=True
    )
    picking_id = fields.Many2one(
        "stock.picking", required=True, ondelete="restrict", check_company=True
    )
    lot_id = fields.Many2one("stock.lot", required=True, ondelete="restrict", check_company=True)
    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    actor_id = fields.Many2one("res.users", required=True, ondelete="restrict")
    arrived_at = fields.Datetime(required=True, string="Llegada efectiva")
    validated_at = fields.Datetime(required=True, string="Validación de Inventario")
    reason = fields.Text(string="Motivo de validación posterior")
    _one_visit = models.Constraint(
        "UNIQUE (repair_id)", "La visita ya tiene una llegada acreditada."
    )
    _one_transfer = models.Constraint(
        "UNIQUE (picking_id, lot_id)", "La recepción de esta serie ya acredita otra visita."
    )
    _valid_chronology = models.Constraint(
        "CHECK (arrived_at <= validated_at)", "La llegada no puede ser posterior a la validación."
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su or self.env.context.get("_mc_arrival_capture") is not _ARRIVAL_CAPTURE:
            raise AccessError(_("Registre la recepción desde la visita de reparación."))
        return super().create(vals_list)

    def write(self, vals):
        # pylint: disable=method-required-super
        raise AccessError(_("La llegada acreditada conserva su evidencia original."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_uninstall(self):
        raise AccessError(_("La llegada acreditada no se elimina."))


class RepairOrderArrival(models.Model):
    """Abre la captura de la llegada desde la visita con acceso a Inventario."""

    _inherit = "repair.order"

    mc_arrived_at = fields.Datetime(compute="_compute_mc_arrival", string="Llegada acreditada")
    mc_arrival_validated_at = fields.Datetime(
        compute="_compute_mc_arrival", string="Validación de la recepción"
    )

    @api.depends("company_id", "lot_id")
    @api.depends_context("uid", "company")
    def _compute_mc_arrival(self):
        # Mostrar los sellos solo con acceso efectivo a la visita y a Inventario.
        arrivals = (
            self.env["mc.rov.repair.arrival"]
            .sudo()
            .search([("repair_id", "in", self.ids), ("company_id", "in", self.env.companies.ids)])
        )
        by_visit = {entry.repair_id.id: entry for entry in arrivals}
        for visit in self:
            entry = by_visit.get(visit.id)
            visible = (
                entry
                and visit.has_access("read")
                and visit.lot_id.has_access("read")
                and entry.lot_id.id == visit.lot_id.id
                and entry.picking_id.with_env(self.env).has_access("read")
            )
            visit.mc_arrived_at = entry.arrived_at if visible else False
            visit.mc_arrival_validated_at = entry.validated_at if visible else False

    def action_mc_record_arrival(self):
        self.ensure_one()
        self.check_access("write")
        self.check_access("read")
        if self.company_id not in self.env.companies or not self.env.user.has_group(
            "stock.group_stock_user"
        ):
            raise AccessError(_("Se requiere acceso a la reparación y a Inventario."))
        defaults = {"default_repair_id": self.id}
        if self.picking_id and self.picking_id.has_access("read"):
            defaults["default_picking_id"] = self.picking_id.id
        return {
            "type": "ir.actions.act_window",
            "name": _("Acreditar llegada al taller"),
            "res_model": "mc.rov.repair.arrival.wizard",
            "views": [(self.env.ref("mc_rov.view_repair_arrival_wizard").id, "form")],
            "target": "new",
            "context": defaults,
        }
