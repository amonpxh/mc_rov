"""Read formal first repair acceptance without rewriting its historical evidence."""

from odoo import _, api, models
from odoo.exceptions import AccessError, ValidationError

from .business_kpi_metrics import first_pass_status


class RepairFirstPassKPI(models.AbstractModel):
    """Classify an explicit authorized selection, separate from stage completion."""

    _name = "mc.rov.repair.acceptance.kpi"
    _description = "Primera aceptación final de reparación"

    def _check_caller(self):
        user = self.env.user
        if (
            user.share
            or user._is_public()
            or not user.has_group("base.group_user")
            or not user.has_group("mc_rov.group_work_assignment_team")
        ):
            raise AccessError(_("Se requiere consulta del trabajo del equipo."))
        return self.env.companies.ids

    def _selected_repairs(self, repair_ids, companies):
        if not isinstance(repair_ids, list) or any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
            for value in repair_ids
        ):
            raise ValidationError(_("Seleccione identificadores válidos de reparación."))
        repairs = (
            self.env["repair.order"]
            .with_context(active_test=False)
            .browse(sorted(set(repair_ids)))
        )
        if len(repairs.exists()) != len(repairs):
            raise AccessError(_("La selección contiene reparaciones no autorizadas."))
        repairs.check_access("read")
        if any(repair.company_id.id not in companies for repair in repairs):
            raise AccessError(_("La selección contiene reparaciones no autorizadas."))
        repairs.lot_id.check_access("read")
        repairs.product_id.check_access("read")
        return repairs

    def _authorized_attempts(self, repairs, companies):
        # Elevate only after authorizing the selected business documents. All
        # historical revisions must remain readable: never silently drop a failure.
        attempts = (
            self.env["mc.rov.repair.acceptance.attempt"]
            .sudo()
            .search(
                [("repair_id", "in", repairs.ids), ("company_id", "in", companies)],
                order="repair_id, ordinal",
            )
        )
        revisions = self.env["mc.rov.revision"].browse(attempts.revision_id.ids)
        revisions.check_access("read")
        revisions.lot_id.check_access("read")
        revisions.product_id.check_access("read")
        sources = {repair.id: repair for repair in repairs}
        for attempt in attempts:
            source = sources[attempt.repair_id.id]
            if attempt.lot_id.id != source.lot_id.id:
                raise AccessError(_("La serie histórica no corresponde a la reparación."))
        return attempts

    def _normalized_attempt(self, attempt):
        if attempt.state == "pending":
            return {"ordinal": attempt.ordinal, "validity": "valid", "verdict": "pending"}
        verdict = attempt.verdict_snapshot
        passed = attempt.state == "confirmed" and verdict in (
            "aprobado",
            "aprobado_con_observaciones",
        )
        failed = attempt.state == "aborted" or verdict == "rechazado"
        return {
            "ordinal": attempt.ordinal,
            "validity": "valid",
            "verdict": "failed" if failed else "passed" if passed else None,
            "required_passed": True if passed else None,
            "required_failure": failed,
            "correction_required": {"yes": True, "no": False}.get(attempt.correction_snapshot),
            "retest_required": {"yes": True, "no": False}.get(attempt.retest_snapshot),
        }

    @api.model
    def get_summary(self, repair_ids):
        companies = self._check_caller()
        repairs = self._selected_repairs(repair_ids, companies)
        attempts = self._authorized_attempts(repairs, companies)
        grouped = {repair.id: [] for repair in repairs}
        for attempt in attempts:
            grouped[attempt.repair_id.id].append(self._normalized_attempt(attempt))
        episodes = []
        for repair in repairs:
            rows = grouped[repair.id]
            episodes.append(
                {
                    "repair_id": repair.id,
                    "lot_id": repair.lot_id.id or False,
                    "status": first_pass_status(rows),
                    "first_ordinal": min((row["ordinal"] for row in rows), default=False),
                }
            )
        counts = {
            key: sum(row["status"] == key for row in episodes)
            for key in ("passed", "failed", "pending", "unknown")
        }
        evaluated = counts["passed"] + counts["failed"]
        return {
            "basis": "selected_repairs_current",
            "population": len(episodes),
            **counts,
            "evaluated": evaluated,
            "value": 100 * counts["passed"] / evaluated if evaluated else None,
            "coverage_percent": 100 * evaluated / len(episodes) if episodes else None,
            "episodes": episodes,
        }
