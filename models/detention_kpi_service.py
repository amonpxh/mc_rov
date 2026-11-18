"""Consulta F2 sobre órdenes autorizadas al corte actual y duración del período."""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain

from .detention_capture import OPEN, SOURCES
from .detention_history import CAUSE_LABELS
from .detention_kpi_metrics import summarize_detentions
from .production_kpi_metrics import local_day, period_bounds


PROCESSES = {"repair": "repair.order", "manufacturing": "mrp.production"}
SANTIAGO = ZoneInfo("America/Santiago")


def _midnight(day):
    return datetime.combine(day, time.min, SANTIAGO).astimezone(timezone.utc)


def _duration_bounds(date_from, date_to, cutoff, intervals):
    """Resuelve fechas civiles de Santiago y conserva el corte actual."""
    start, end = period_bounds(date_from, date_to)
    today = local_day(cutoff)
    if not start:
        earliest = min([today, *(local_day(row["start"]) for row in intervals)])
        start = min(earliest, end) if end else earliest
    end = end or max(today, start)
    return _midnight(start), _midnight(end + timedelta(days=1))


class DetentionKPIService(models.AbstractModel):
    """Agrega intervalos confirmados sin divulgar filas del historial privado."""

    _name = "mc.rov.detention.kpi"
    _description = "Indicador de detenciones efectivas ROV"

    def _population(self, model, companies):
        service = self.env["mc.rov.detention.service"]
        field = SOURCES[model]
        history = service._ledger().search(
            [
                ("company_id", "in", companies),
                (field, "!=", False),
            ]
        )
        historical_ids = history[field].ids
        root = self.env["stock.lot"]._get_rov_root_category()
        active = [("product_id.categ_id", "child_of", root.id)] if root else [("id", "=", 0)]
        orders = (
            self.env[model]
            .with_context(active_test=False)
            .search(
                Domain.AND(
                    [
                        [("company_id", "in", companies)],
                        Domain.OR([active, [("id", "in", historical_ids)]]),
                    ]
                )
            )
        )
        if not set(historical_ids) <= set(orders.ids):
            raise AccessError(_("Falta acceso a órdenes con evidencia de detenciones."))
        # Detectar incoherencias de empresa sin incluir la evidencia de otra empresa.
        evidence = service._ledger().search([(field, "in", orders.ids)])
        by_id = {order.id: order for order in orders}
        intervals = []
        for row in evidence:
            identity = row[field].id
            if row.company_id.id != by_id[identity].company_id.id:
                raise AccessError(_("La empresa del historial no coincide con la orden."))
            intervals.append(
                {
                    "identity": row.id,
                    "order": (model, identity),
                    "cause": row.cause,
                    "start": row.started_at,
                    "end": row.ended_at or None,
                }
            )
        return [
            {"identity": (model, row.id), "open_at_cutoff": row.state in OPEN[model]}
            for row in orders
        ], intervals

    @api.model
    def get_summary(self, date_from=False, date_to=False, process="all"):
        companies = self.env["mc.rov.kpi.dashboard"]._check_caller()
        if not isinstance(process, str) or process not in ("all", *PROCESSES):
            raise ValidationError(_("Seleccione Reparación, Fabricación o ambos procesos."))
        cutoff = fields.Datetime.now()
        groups = [
            self._population(PROCESSES[key], companies)
            for key in (PROCESSES if process == "all" else (process,))
        ]
        orders = [order for group in groups for order in group[0]]
        intervals = [row for group in groups for row in group[1]]
        try:
            start_bound, end_bound = _duration_bounds(date_from, date_to, cutoff, intervals)
        except (OverflowError, TypeError, ValueError) as exc:
            raise ValidationError(_("Seleccione un período válido.")) from exc
        try:
            result = summarize_detentions(orders, intervals, start_bound, end_bound, cutoff)
        except ValueError as exc:
            raise ValidationError(_("La evidencia de detenciones requiere revisión.")) from exc
        result.pop("by_order")
        for cause, values in result["by_cause"].items():
            values["label"] = _(CAUSE_LABELS[cause])
        return result
