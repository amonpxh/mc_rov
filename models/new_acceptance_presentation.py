"""Present joint acceptance from authorized sources without opening private history ACLs."""

# Identity, capture and presentation are distinct validation boundaries.
# pylint: disable=unknown-option-value,consider-merging-classes-inherited
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class NewAcceptancePresentation(models.Model):
    """Show formal source participation and immutable unit history in the native review."""

    _inherit = "mc.rov.revision"

    mc_new_attempt_pending = fields.Boolean(compute="_compute_new_acceptance_state")
    mc_new_phase_recorded = fields.Boolean(compute="_compute_new_acceptance_state")
    mc_new_acceptance_state = fields.Selection(
        [("pending", "En comprobación"), ("confirmed", "Confirmado"), ("failed", "Fallido")],
        string="Estado conjunto",
        compute="_compute_new_acceptance_state",
    )
    mc_new_failure_reason = fields.Text(
        string="Motivo del fallo",
        copy=False,
        help="Explique el fallo real que impidió completar la aceptación de equipo nuevo.",
    )
    mc_new_acceptance_history_html = fields.Html(
        string="Intentos de aceptación de equipo nuevo",
        compute="_compute_new_acceptance_history",
        readonly=True,
        groups="mc_rov.group_work_assignment_team",
    )

    def _new_presentation_attempts(self, history=False):
        self.ensure_one()
        attempts = self.env["mc.rov.new.acceptance.attempt"].sudo()
        if not isinstance(self.id, int) or self.id <= 0 or not self.lot_id:
            return attempts
        self.check_access("read")
        if history and not self.env.user.has_group("mc_rov.group_work_assignment_team"):
            raise AccessError(_("Se requiere consulta del trabajo del equipo."))
        domain = (
            [("episode_id.lot_id", "=", self.lot_id.id)]
            if history
            else [
                "|",
                ("rnd_id", "=", self.id),
                ("trn_id", "=", self.id),
            ]
        )
        attempts = attempts.search(domain, order="ordinal")
        if not attempts:
            return attempts
        if self.env.user.share or self.env.user._is_public():
            raise AccessError(_("La aceptación requiere una cuenta interna."))
        if any(row.company_id.id not in self.env.companies.ids for row in attempts):
            raise AccessError(_("La aceptación no pertenece a una empresa activa autorizada."))
        for episode in attempts.episode_id:
            for record in (episode.production_id, episode.lot_id, episode.product_id):
                self.env[record._name].browse(record.ids).check_access("read")
        # History contains both protocols, so permission on only one is insufficient.
        self.env["mc.rov.revision"].browse((attempts.rnd_id | attempts.trn_id).ids).check_access(
            "read"
        )
        return attempts

    @api.depends("lot_id", "tipo", "repair_id", "estado")
    @api.depends_context("uid", "allowed_company_ids")
    def _compute_new_acceptance_state(self):
        # Read-only lookup: displaying a form must never acquire write locks.
        for revision in self:
            revision.mc_new_attempt_pending = False
            revision.mc_new_phase_recorded = False
            revision.mc_new_acceptance_state = False
            if revision.tipo not in ("rendimiento", "terreno") or revision.repair_id:
                continue
            attempts = revision._new_presentation_attempts()
            if attempts:
                attempt = attempts[-1]
                phase = "performance" if revision.id == attempt.rnd_id.id else "field"
                revision.mc_new_acceptance_state = attempt.state
                revision.mc_new_attempt_pending = attempt.state == "pending"
                revision.mc_new_phase_recorded = phase in attempt.requirements_snapshot.get(
                    "results", {}
                )

    def _new_history_markup(self, attempts):
        states = {
            "pending": _("En comprobación"),
            "confirmed": _("Confirmado"),
            "failed": _("Fallido"),
        }
        first_pass = {
            "unknown": _("Sin determinar"),
            "passed": _("Aprobado"),
            "failed": _("Fallido"),
        }
        verdicts = {
            "aprobado": _("Aprobado"),
            "aprobado_con_observaciones": _("Aprobado con observaciones"),
            "rechazado": _("Rechazado"),
        }
        rows = []
        for attempt in attempts:
            results = attempt.requirements_snapshot.get("results", {})
            reasons = " · ".join(row["reason"] for row in results.values() if row.get("reason"))
            rows.append(
                Markup(
                    "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td>"
                    "<td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>"
                ).format(
                    attempt.ordinal,
                    states[attempt.state],
                    verdicts.get(
                        results.get("performance", {}).get("verdict"), _("Sin resultado")
                    ),
                    verdicts.get(results.get("field", {}).get("verdict"), _("Sin resultado")),
                    first_pass[attempt.first_pass_snapshot],
                    self._acceptance_display_date(attempt.started_at),
                    self._acceptance_display_date(attempt.closed_at),
                    attempt.finished_by_id.name or attempt.actor_id.name,
                    reasons,
                )
            )
        headers = Markup("").join(
            Markup("<th>{}</th>").format(label)
            for label in (
                _("Intento"),
                _("Estado conjunto"),
                _("Rendimiento"),
                _("Terreno"),
                _("Primer pase"),
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

    @api.depends("lot_id", "tipo", "repair_id", "estado")
    @api.depends_context("uid", "allowed_company_ids", "lang", "tz")
    def _compute_new_acceptance_history(self):
        for revision in self:
            revision.mc_new_acceptance_history_html = False
            if revision.tipo in ("rendimiento", "terreno") and not revision.repair_id:
                attempts = revision._new_presentation_attempts(history=True)
                revision.mc_new_acceptance_history_html = (
                    revision._new_history_markup(attempts)
                    if attempts
                    else Markup("<p>{}</p>").format(_("Todavía no hay intentos iniciados."))
                )

    def _invalidate_new_acceptance_presentation(self):
        # A result in RND can change the cached joint state displayed on TRN, and vice versa.
        sources = self | self.sudo().search([("lot_id", "in", self.lot_id.ids)])
        sources.invalidate_recordset(
            [
                "mc_new_attempt_pending",
                "mc_new_phase_recorded",
                "mc_new_acceptance_state",
                "mc_new_acceptance_history_html",
            ]
        )

    def action_confirmar(self):
        result = super().action_confirmar()
        self._invalidate_new_acceptance_presentation()
        return result

    def action_abort_new_acceptance(self, reason):
        result = super().action_abort_new_acceptance(reason)
        self._invalidate_new_acceptance_presentation()
        return result

    def action_record_new_acceptance_failure(self):
        self.ensure_one()
        return self.action_abort_new_acceptance(self.mc_new_failure_reason or "")


class NewAcceptancePresentationService(models.AbstractModel):
    """Invalidate both source forms after the explicit joint start."""

    _inherit = "mc.rov.new.acceptance"

    @api.model
    def start_attempt(self, production_id, lot_id, rnd_id, trn_id):
        result = super().start_attempt(production_id, lot_id, rnd_id, trn_id)
        self.env["mc.rov.revision"].browse(
            [rnd_id, trn_id]
        )._invalidate_new_acceptance_presentation()
        return result
