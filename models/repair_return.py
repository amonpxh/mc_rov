"""Q2 vincula una visita de retorno con la intervención original acreditada."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .business_kpi_metrics import observed_return_summary
from .production_kpi_event import lock_source
from .production_kpi_metrics import local_day, period_bounds


_RETURN_CAPTURE = object()
SUPERVISOR_GROUP = "mc_rov.group_repair_return_supervisor"
VERDICTS = [("confirmed", "Relacionada con la reparación"), ("unrelated", "Otra causa")]
RELATIONS = [("pending", "Dictamen pendiente"), *VERDICTS]


class RepairReturn(models.Model):
    """Evidencia privada de vínculo y dictamen, con autores independientes."""

    _name = "mc.rov.repair.return"
    _description = "Retorno documentado de ROV"
    _check_company_auto = True

    return_id = fields.Many2one(
        "repair.order", required=True, ondelete="restrict", check_company=True
    )
    original_id = fields.Many2one(
        "repair.order", required=True, ondelete="restrict", check_company=True
    )
    company_id = fields.Many2one("res.company", required=True, ondelete="restrict", index=True)
    lot_id = fields.Many2one("stock.lot", required=True, ondelete="restrict", check_company=True)
    dispatch_id = fields.Many2one("mc.rov.customer.dispatch", required=True, ondelete="restrict")
    arrival_id = fields.Many2one("mc.rov.repair.arrival", required=True, ondelete="restrict")
    linked_by = fields.Many2one("res.users", required=True, ondelete="restrict")
    relation = fields.Selection(RELATIONS, required=True, default="pending")
    reason = fields.Text()
    decided_by = fields.Many2one("res.users", ondelete="restrict")
    decided_at = fields.Datetime()

    _one_return = models.Constraint(
        "UNIQUE (return_id)", "La visita ya tiene un retorno vinculado."
    )
    _distinct_visits = models.Constraint(
        "CHECK (original_id <> return_id)", "Seleccione otra visita."
    )

    def _capture(self):
        return self.sudo().with_context({}, mc_return_capture=_RETURN_CAPTURE)

    def _require_capture(self):
        if not self.env.su or self.env.context.get("mc_return_capture") is not _RETURN_CAPTURE:
            raise AccessError(_("Use las acciones de retorno de la visita."))

    @api.model_create_multi
    def create(self, vals_list):
        self._require_capture()
        return super().create(vals_list)

    def write(self, vals):
        self._require_capture()
        if set(vals) != {"relation", "reason", "decided_by", "decided_at"} or any(
            row.relation != "pending" for row in self
        ):
            raise AccessError(_("El vínculo y el dictamen conservan su evidencia original."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_uninstall(self):
        raise AccessError(_("El historial de retornos se conserva."))

    def _check_operator(self, returned, *, decide=False):
        returned.ensure_one()
        user = self.env.user
        if user.share or not user.has_group(
            SUPERVISOR_GROUP if decide else "stock.group_stock_user"
        ):
            raise AccessError(
                _("Se requiere el permiso correspondiente para registrar el retorno.")
            )
        returned.check_access("write")
        returned.check_access("read")
        if returned.company_id not in self.env.companies:
            raise AccessError(_("La visita pertenece a otra empresa."))

    def _entry_for(self, returned):
        return self.sudo().search([("return_id", "=", returned.id)], limit=1)

    def _link(self, returned, original):
        self._check_operator(returned)
        original.ensure_one()
        original.check_access("read")
        lock_source(returned)
        lot = returned.lot_id
        lot.check_access("read")
        if (
            not lot.es_un_rov
            or original == returned
            or original.lot_id != lot
            or original.company_id != returned.company_id
            or "cancel" in (original.state, returned.state)
        ):
            raise UserError(_("Seleccione una reparación anterior de la misma serie y empresa."))
        entry = self._entry_for(returned)
        if entry:
            if entry.original_id.id != original.id or not self._can_read_entry(entry):
                raise UserError(_("La visita ya cuenta con un vínculo de retorno."))
            return
        arrival = (
            self.env["mc.rov.repair.arrival"].sudo().search([("repair_id", "=", returned.id)])
        )
        if (
            not arrival
            or arrival.lot_id.id != lot.id
            or not arrival.picking_id.with_env(self.env).has_access("read")
        ):
            raise UserError(_("La visita de retorno requiere una llegada acreditada y accesible."))
        dispatches = (
            self.env["mc.rov.repair.lead.time.kpi"]
            ._departure_events(returned.company_id.ids, [original.id])
            .get(original.id, [])
        )
        if len(dispatches) != 1:
            raise UserError(_("La visita original requiere una sola salida vigente y accesible."))
        dispatch = dispatches[0]
        reversed_order = (
            dispatch.effective_at > arrival.arrived_at
            if dispatch.effective_at
            else dispatch.effective_date > local_day(arrival.arrived_at)
        )
        if reversed_order:
            raise UserError(_("La llegada del retorno debe ser posterior a la salida original."))
        self._capture().create(
            {
                "return_id": returned.id,
                "original_id": original.id,
                "company_id": returned.company_id.id,
                "lot_id": lot.id,
                "dispatch_id": dispatch.id,
                "arrival_id": arrival.id,
                "linked_by": self.env.uid,
            }
        )

    def _can_read_entry(self, entry):
        original = entry.original_id.with_env(self.env)
        returned = entry.return_id.with_env(self.env)
        lot = entry.lot_id.with_env(self.env)
        return (
            entry.company_id.id in self.env.companies.ids
            and original.has_access("read")
            and returned.has_access("read")
            and lot.has_access("read")
            and (entry.dispatch_id.picking_id | entry.arrival_id.picking_id)
            .with_env(self.env)
            .has_access("read")
            and original.lot_id == returned.lot_id == lot
            and original.company_id == returned.company_id
        )

    def _decide(self, returned, relation, reason):
        self._check_operator(returned, decide=True)
        lock_source(returned)
        entry = self._entry_for(returned)
        if not entry or not self._can_read_entry(entry):
            raise AccessError(_("Se requiere acceso a ambas visitas y a su evidencia."))
        reason = (reason or "").strip()
        if relation not in dict(VERDICTS) or not reason:
            raise UserError(_("Indique el resultado y el fundamento del dictamen."))
        if (
            entry.relation == relation
            and entry.reason == reason
            and entry.decided_by.id == self.env.uid
        ):
            return
        if entry.relation != "pending":
            raise UserError(_("La visita ya tiene un dictamen registrado."))
        departures = self.env["mc.rov.repair.lead.time.kpi"]._departure_events(
            returned.company_id.ids, [entry.original_id.id]
        )
        if returned.state == "cancel" or departures.get(entry.original_id.id) != [
            entry.dispatch_id
        ]:
            raise UserError(_("La visita o la constancia original dejaron de estar vigentes."))
        entry.with_env(self.env)._capture().write(
            {
                "relation": relation,
                "reason": reason,
                "decided_by": self.env.uid,
                "decided_at": fields.Datetime.now(),
            }
        )

    @api.model
    def get_summary(self, date_from=False, date_to=False):
        companies = self.env["mc.rov.kpi.dashboard"]._check_caller()
        if not all(
            self.env[model].has_access("read")
            for model in ("repair.order", "stock.picking", "stock.lot")
        ):
            raise AccessError(_("Se requiere lectura de Reparación e Inventario."))
        try:
            start, end = period_bounds(date_from, date_to)
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("Seleccione un período válido.")) from exc
        today = local_day(fields.Datetime.now())
        cutoff = min(end, today) if end else today
        entries = self.sudo().search([("company_id", "in", companies)])
        originals = self.env["mc.rov.repair.lead.time.kpi"]._departure_events(
            companies, entries.original_id.ids
        )
        departures = {}
        events = []
        for entry in entries:
            returned_on = local_day(entry.arrival_id.arrived_at)
            if (
                (start and returned_on < start)
                or returned_on > cutoff
                or not self._can_read_entry(entry)
            ):
                continue
            if (
                originals.get(entry.original_id.id) != [entry.dispatch_id]
                or entry.return_id.state == "cancel"
            ):
                continue
            departures[entry.original_id.id] = local_day(
                entry.dispatch_id.effective_at or entry.dispatch_id.effective_date
            )
            events.append(
                {
                    "event_id": entry.id,
                    "visit_id": entry.original_id.id,
                    "returned_on": returned_on,
                    "relation": entry.relation,
                }
            )
        return observed_return_summary(departures, events, as_of=cutoff)


class RepairOrderReturn(models.Model):
    """Presenta el estado del retorno sobre la visita del equipo."""

    _inherit = "repair.order"

    mc_return_relation = fields.Selection(
        RELATIONS, compute="_compute_mc_return", string="Dictamen de retorno"
    )
    mc_return_original_id = fields.Many2one(
        "repair.order", compute="_compute_mc_return", string="Reparación anterior"
    )
    mc_return_reason = fields.Text(compute="_compute_mc_return", string="Fundamento del dictamen")

    @api.depends_context("uid", "company")
    def _compute_mc_return(self):
        ledger = self.env["mc.rov.repair.return"]
        entries = ledger.sudo().search([("return_id", "in", self.ids)])
        visible = {entry.return_id.id: entry for entry in entries if ledger._can_read_entry(entry)}
        for repair in self:
            entry = visible.get(repair.id)
            repair.mc_return_relation = entry.relation if entry else False
            repair.mc_return_original_id = entry.original_id.id if entry else False
            repair.mc_return_reason = entry.reason if entry else False

    def _open_mc_return(self, *, decide=False):
        self.env["mc.rov.repair.return"]._check_operator(self, decide=decide)
        return {
            "type": "ir.actions.act_window",
            "res_model": "mc.rov.repair.return.wizard",
            "name": _("Dictaminar retorno") if decide else _("Vincular retorno"),
            "views": [(self.env.ref("mc_rov.view_repair_return_wizard").id, "form")],
            "target": "new",
            "context": {"default_return_id": self.id, "default_decide": decide},
        }

    def action_mc_link_return(self):
        return self._open_mc_return()

    def action_mc_decide_return(self):
        return self._open_mc_return(decide=True)
