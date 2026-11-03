"""Aggregate only runs whose business documents the caller can read."""

from datetime import date, datetime

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .work_kpi_metrics import build_metrics


_FLOWS = {
    "repair": ("repair.order", "repair_id", "Reparación"),
    "manufacturing": ("mrp.production", "production_id", "Fabricación"),
    "acceptance": ("stock.lot", "cycle_id.lot_id", "Aceptación"),
    "quality": ("quality.alert", "alert_id", "Calidad"),
    "engineering": ("mrp.eco", "eco_id", "Ingeniería"),
    "inventory": ("stock.picking", "picking_id", "Inventario"),
}


class WorkKPI(models.AbstractModel):
    """Team indicators without granting access to private technical history."""

    _name = "mc.rov.work.kpi"
    _description = "Indicadores de seguimiento del trabajo"

    def _now(self):
        return fields.Datetime.now()

    def _check_team(self):
        if not self.env.user.has_group("base.group_user") or not self.env.user.has_group(
            "mc_rov.group_work_assignment_team"
        ):
            raise AccessError(_("No tiene permiso para consultar indicadores del equipo."))
        # Resolving companies validates RPC context against the caller's membership.
        return self.env.companies.ids

    def _date_bound(self, value):
        if value is False or value is None:
            return None
        try:
            if not isinstance(value, str) or len(value) != 10:
                raise ValueError
            parsed = date.fromisoformat(value)
            if parsed.isoformat() != value:
                raise ValueError
            return parsed
        except ValueError as error:
            raise ValidationError(_("Las fechas deben tener formato AAAA-MM-DD.")) from error

    def _local_date(self, instant, zone):
        if not instant or not zone:
            return None
        try:
            instant = fields.Datetime.to_datetime(instant)
            if instant.tzinfo is None:
                instant = pytz.utc.localize(instant)
            return instant.astimezone(pytz.timezone(zone)).date()
        except (ValueError, TypeError, pytz.UnknownTimeZoneError):
            return None

    def _authorized_runs(self, process, companies):
        model, relation, _label = _FLOWS[process]
        sources = self.env[model].with_context(active_test=False)
        if not sources.has_access("read"):
            return None
        source_ids = sources.search([("company_id", "in", companies + [False])]).ids
        # No write gateway, ACL change or private ID escapes this boundary. Both
        # company and document predicates are required before elevating run reads.
        runs = (
            self.env["mc.rov." + process + ".activity.run"]
            .sudo()
            .search([("company_id", "in", companies), (relation, "in", source_ids)])
        )
        return runs

    def _visible_activities(self, runs):
        activities = self.env["mail.activity"]
        if not activities.has_access("read"):
            return {}
        allowed = activities.search([("id", "in", runs.activity_id.ids), ("active", "=", True)])
        return {activity.id: activity for activity in allowed}

    def _row(self, process, run, activities, window):
        source = run.mapped(_FLOWS[process][1])
        zone = (
            run.cycle_id.deadline_tz
            if process in ("engineering", "inventory")
            else run.calendar_tz
        )
        finished_date = self._local_date(run.finished_at, zone)
        activity = activities.get(run.activity_id.id)
        matches = bool(
            activity and activity.res_model == _FLOWS[process][0] and activity.res_id == source.id
        )
        # Unknown dates cannot be assigned to a bounded period. The report keeps
        # their count separately, rather than implying complete historical coverage.
        in_period = not (window["lower"] or window["upper"]) or bool(
            finished_date
            and (not window["lower"] or finished_date >= window["lower"])
            and (not window["upper"] or finished_date <= window["upper"])
        )
        return {
            "outcome": run.outcome,
            "in_period": in_period,
            "started_at": run.started_at or None,
            "finished_at": run.finished_at or None,
            "finished_date": finished_date,
            "as_of_date": self._local_date(window["now"], zone),
            "original_deadline": run.original_deadline or None,
            "current_deadline": (run.current_deadline or None if process != "repair" else None),
            "activity_active": matches,
            "pending_deadline": activity.date_deadline if matches else None,
        }

    @api.model
    def get_summary(self, date_from=False, date_to=False, process="all"):
        companies = self._check_team()
        if not isinstance(process, str) or process not in ("all", *_FLOWS):
            raise ValidationError(_("El proceso de indicadores no es válido."))
        lower, upper = self._date_bound(date_from), self._date_bound(date_to)
        if lower and upper and lower > upper:
            raise ValidationError(_("La fecha inicial debe ser anterior a la final."))
        now = self._now()
        if not isinstance(now, datetime):
            now = fields.Datetime.to_datetime(now)
        result = {
            "generated_at": fields.Datetime.to_string(now),
            "period": {
                "date_from": lower.isoformat() if lower else False,
                "date_to": upper.isoformat() if upper else False,
            },
            "processes": [],
            "partial": False,
        }
        for key in _FLOWS if process == "all" else (process,):
            runs = self._authorized_runs(key, companies)
            if runs is None and process != "all":
                raise AccessError(_("No tiene acceso de lectura a este proceso."))
            row = {"key": key, "available": runs is not None, "metrics": None}
            if runs is not None:
                activities = self._visible_activities(runs)
                window = {"now": now, "lower": lower, "upper": upper}
                rows = [self._row(key, run, activities, window) for run in runs]
                row["metrics"] = build_metrics(rows)
                row["period_unlocated"] = sum(
                    item["outcome"] != "pending" and not item["finished_date"] for item in rows
                )
            else:
                result["partial"] = True
            result["processes"].append(row)
        return result
