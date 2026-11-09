"""Native revision presentation for explicit final acceptance and protected history."""

from markupsafe import Markup

from odoo import _, api, fields, models


class RepairAcceptancePresentation(models.Model):
    """Display attempts from their authorized source without exposing private model ACLs."""

    _inherit = "mc.rov.revision"

    mc_final_attempt_pending = fields.Boolean(compute="_compute_final_attempt_state")
    mc_final_identity_locked = fields.Boolean(compute="_compute_final_attempt_state")
    mc_final_failure_reason = fields.Text(
        string="Motivo del fallo",
        copy=False,
        help="Explique el fallo real que obligó a detener la comprobación final.",
    )
    mc_acceptance_history_html = fields.Html(
        string="Intentos de aceptación final",
        compute="_compute_acceptance_history_html",
        groups="mc_rov.group_work_assignment_team",
        readonly=True,
    )

    @api.depends("mc_acceptance_purpose", "repair_id", "lot_id", "estado")
    @api.depends_context("uid", "allowed_company_ids")
    def _compute_final_attempt_state(self):
        # Only disclose document-level state after authorizing its source and company.
        for revision in self:
            revision.mc_final_attempt_pending = False
            revision.mc_final_identity_locked = False
            if (
                isinstance(revision.id, int)
                and revision.id > 0
                and revision.mc_acceptance_purpose == "final"
                and revision.repair_id
                and revision.lot_id
            ):
                revision._acceptance_source_access("read")
                attempts = revision._acceptance_attempts().filtered(
                    lambda row, source=revision: row.revision_id == source
                )
                revision.mc_final_attempt_pending = any(row.state == "pending" for row in attempts)
                revision.mc_final_identity_locked = bool(attempts)

    def _acceptance_display_date(self, value):
        return (
            fields.Datetime.context_timestamp(self, value).strftime("%d-%m-%Y %H:%M")
            if value
            else ""
        )

    def _acceptance_history_markup(self, attempts):
        states = {
            "pending": _("En comprobación"),
            "confirmed": _("Confirmado"),
            "aborted": _("Interrumpido por fallo"),
        }
        verdicts = {
            "aprobado": _("Aprobado"),
            "aprobado_con_observaciones": _("Aprobado con observaciones"),
            "rechazado": _("Rechazado"),
        }
        flags = {"unknown": _("Por revisar"), "no": _("No"), "yes": _("Sí")}
        rows = []
        for attempt in attempts:
            # Every interpolated value is escaped, including free text and account names.
            rows.append(
                Markup(
                    "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td>"
                    "<td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>"
                ).format(
                    attempt.ordinal,
                    states[attempt.state],
                    verdicts.get(attempt.verdict_snapshot, ""),
                    flags.get(attempt.correction_snapshot, ""),
                    flags.get(attempt.retest_snapshot, ""),
                    self._acceptance_display_date(attempt.started_at),
                    self._acceptance_display_date(attempt.closed_at),
                    attempt.actor_id.name,
                    attempt.reason or "",
                )
            )
        headers = Markup("").join(
            Markup("<th>{}</th>").format(label)
            for label in (
                _("Intento"),
                _("Estado"),
                _("Resultado"),
                _("Requiere corrección"),
                _("Requiere reensayo"),
                _("Inicio"),
                _("Cierre"),
                _("Registrado por"),
                _("Motivo"),
            )
        )
        return Markup(
            '<div class="table-responsive"><table class="table table-sm">'
            "<thead><tr>{}</tr></thead><tbody>{}</tbody></table></div>"
        ).format(headers, Markup("").join(rows))

    @api.depends("mc_acceptance_purpose", "repair_id", "lot_id", "estado")
    @api.depends_context("uid", "allowed_company_ids", "lang", "tz")
    def _compute_acceptance_history_html(self):
        # A denied source is an access error, never an apparently empty history.
        for revision in self:
            revision.mc_acceptance_history_html = False
            if (
                isinstance(revision.id, int)
                and revision.id > 0
                and revision.mc_acceptance_purpose == "final"
                and revision.repair_id
                and revision.lot_id
            ):
                attempts = revision._get_repair_acceptance_attempts(revision.repair_id)
                revision.mc_acceptance_history_html = (
                    revision._acceptance_history_markup(attempts)
                    if attempts
                    else Markup("<p>{}</p>").format(_("Todavía no hay intentos iniciados."))
                )

    def _invalidate_acceptance_presentation(self):
        self.invalidate_recordset(
            ["mc_final_attempt_pending", "mc_final_identity_locked", "mc_acceptance_history_html"]
        )

    def action_start_final_acceptance(self):
        self.ensure_one()
        self._invalidate_acceptance_presentation()
        was_pending = self.mc_final_attempt_pending
        result = super().action_start_final_acceptance()
        if not was_pending:
            self.mc_final_failure_reason = False
        self._invalidate_acceptance_presentation()
        return result

    def action_confirmar(self):
        result = super().action_confirmar()
        self._invalidate_acceptance_presentation()
        return result

    def action_abort_final_acceptance(self, reason):
        result = super().action_abort_final_acceptance(reason)
        self._invalidate_acceptance_presentation()
        return result

    def action_record_final_failure(self):
        self.ensure_one()
        return self.action_abort_final_acceptance(self.mc_final_failure_reason or "")
