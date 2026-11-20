"""F6 concilia los extremos de la visita sin depender de una promesa comercial."""

from collections import defaultdict

from odoo import _, api, models
from odoo.exceptions import AccessError, ValidationError

from .production_kpi_metrics import local_day, period_bounds
from .repair_lead_time_metrics import summarize


class RepairLeadTimeKPI(models.AbstractModel):
    """Consulta duraciones solo para documentos y series accesibles."""

    _name = "mc.rov.repair.lead.time.kpi"
    _description = "Plazo de reparación entre llegada y salida"

    def _departure_events(self, companies, repair_ids=None):
        ledger = self.env["mc.rov.customer.dispatch"].sudo()
        domain = [("company_id", "in", companies)]
        if repair_ids is not None:
            # Buscar el último evento incluso si una corrección cambió las visitas vinculadas.
            picking_ids = ledger.search(domain + [("repair_ids", "in", repair_ids)]).picking_id.ids
            domain.append(("picking_id", "in", picking_ids))
        events = ledger.search(domain, order="id desc")
        latest = {}
        for event in events:
            latest.setdefault(event.picking_id.id, event)
        departures = defaultdict(list)
        for event in latest.values():
            if event.kind == "invalidated" or not event.repair_ids:
                continue
            picking = event.picking_id.with_env(self.env)
            if not picking.has_access("read"):
                continue
            try:
                if picking.state != "done" or not event._evidence_matches(picking):
                    continue
                repairs = (
                    self.env["repair.order"]
                    .with_context(active_test=False)
                    .search(
                        [("id", "in", event.repair_ids.ids), ("state", "!=", "cancel")]
                        + picking._dispatch_repair_domain()
                    )
                )
                for repair in repairs:
                    if (
                        repair_ids is None or repair.id in repair_ids
                    ) and repair.lot_id.has_access("read"):
                        departures[repair.id].append(event)
            except AccessError:
                continue
        return departures

    def _departures(self, companies):
        return {
            visit_id: [event.effective_at or event.effective_date for event in events]
            for visit_id, events in self._departure_events(companies).items()
        }

    def _arrivals(self, departures, companies):
        result = {}
        entries = (
            self.env["mc.rov.repair.arrival"]
            .sudo()
            .search([("repair_id", "in", list(departures)), ("company_id", "in", companies)])
        )
        for entry in entries:
            picking = entry.picking_id.with_env(self.env)
            repair = entry.repair_id.with_env(self.env)
            if picking.has_access("read") and entry.lot_id.id == repair.lot_id.id:
                result[repair.id] = entry.arrived_at
        return result

    @api.model
    def get_summary(self, date_from=False, date_to=False):
        companies = self.env["mc.rov.kpi.dashboard"]._check_caller()
        if not all(
            self.env[model].has_access("read") for model in ("repair.order", "stock.picking")
        ):
            raise AccessError(_("Se requiere lectura de Reparación e Inventario."))
        try:
            start, end = period_bounds(date_from, date_to)
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("Seleccione un período válido.")) from exc
        departures = self._departures(companies)
        arrivals = self._arrivals(departures, companies)
        pairs = []
        ambiguous = 0
        for visit, dates in departures.items():
            days = [local_day(value) for value in dates]
            if not any((not start or day >= start) and (not end or day <= end) for day in days):
                continue
            if len(dates) > 1:
                ambiguous += 1
            else:
                pairs.append((arrivals.get(visit), dates[0]))
        return {
            **summarize(pairs),
            "ambiguous_departure": ambiguous,
            "departed": len(pairs) + ambiguous,
        }
