"""Q3 conserva las decisiones sobre líneas de trabajo de Reparación."""

# pylint: disable=unknown-option-value
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .production_kpi_event import lock_source


CAPTURE = object()
SUPERVISOR = "mc_rov.group_repair_rework_supervisor"
KINDS = [
    ("planned", "Trabajo previsto"),
    ("additional", "Trabajo adicional"),
    ("rework", "Retrabajo"),
]
STATES = [("proposal", "Retrabajo por confirmar"), *KINDS]


class RepairReworkEvent(models.Model):
    """Historial privado de propuestas y confirmaciones de una línea."""

    _name = "mc.rov.repair.rework.event"
    _description = "Clasificación de trabajo en reparación ROV"
    _order = "id desc"

    line_id = fields.Many2one("mc.rov.linea.falla", index=True, ondelete="set null")
    repair_id = fields.Many2one("repair.order", ondelete="set null")
    lot_id = fields.Many2one("stock.lot", required=True, ondelete="restrict")
    company_id = fields.Many2one("res.company", required=True, index=True, ondelete="restrict")
    actor_id = fields.Many2one("res.users", required=True, ondelete="restrict")
    state = fields.Selection(STATES, required=True)
    previous_line_id = fields.Many2one("mc.rov.linea.falla", ondelete="set null")
    finding_id = fields.Many2one("mc.rov.revision.hallazgo", ondelete="set null")
    alert_id = fields.Many2one("quality.alert", ondelete="set null")
    reason = fields.Text()
    proposal_id = fields.Many2one("mc.rov.repair.rework.event", ondelete="restrict")

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su or self.env.context.get("mc_rework_capture") is not CAPTURE:
            raise AccessError(_("Registre la clasificación desde la línea de trabajo."))
        return super().create(vals_list)

    def write(self, vals):
        # pylint: disable=method-required-super
        raise AccessError(_("El historial de retrabajo conserva las decisiones originales."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_uninstall(self):
        raise AccessError(_("El historial de retrabajo se conserva."))

    def _latest(self, lines):
        rows = self.sudo().search(
            [("line_id", "in", lines.ids), ("company_id", "in", self.env.companies.ids)]
        )
        latest = {}
        for row in rows:
            # Una línea reasignada a otra visita o serie pierde su clasificación aplicable.
            latest.setdefault(row.line_id.id, row)
        return {
            line.id: row
            for line in lines
            if (row := latest.get(line.id))
            and row.repair_id.id == line.repair_id.id
            and row.lot_id.id == line.repair_id.lot_id.id
            and row.company_id.id == line.repair_id.company_id.id
        }

    def _append(self, line, state, **evidence):
        self.sudo().with_context({}, mc_rework_capture=CAPTURE).create(
            {
                "line_id": line.id,
                "repair_id": line.repair_id.id,
                "lot_id": line.repair_id.lot_id.id,
                "company_id": line.repair_id.company_id.id,
                "actor_id": self.env.uid,
                "state": state,
                **evidence,
            }
        )

    def _evidence_for(self, line, previous, reason):
        repair = line.repair_id
        if previous:
            previous.check_access("read")
            previous.repair_id.check_access("read")
            if (
                previous == line
                or previous.repair_id.lot_id != repair.lot_id
                or previous.repair_id.company_id != repair.company_id
            ):
                raise UserError(_("Seleccione un trabajo anterior de la misma serie y empresa."))
            if previous.fecha and line.fecha and previous.fecha > line.fecha:
                raise UserError(_("El trabajo anterior no puede tener una fecha posterior."))
        finding = line.hallazgo_origen_id if not previous else self.env["mc.rov.revision.hallazgo"]
        alert = line.mc_alerta_id if not previous and not finding else self.env["quality.alert"]
        if finding:
            finding.check_access("read")
            finding.revision_id.check_access("read")
            finding_order = finding.revision_id.repair_id
            if finding_order:
                finding_order.check_access("read")
            if finding.lot_id != repair.lot_id or (
                finding_order and finding_order.company_id != repair.company_id
            ):
                raise UserError(_("El hallazgo debe corresponder a la misma serie."))
        if alert:
            alert.check_access("read")
            if repair.lot_id not in alert.lot_ids or alert.company_id != repair.company_id:
                raise UserError(_("La alerta debe corresponder a la misma serie y empresa."))
        reason = (reason or "").strip()
        if not reason or not (previous or finding or alert):
            raise UserError(
                _("Agregue el fundamento y un trabajo anterior, hallazgo o alerta de la línea.")
            )
        return {
            "previous_line_id": previous.id,
            "finding_id": finding.id,
            "alert_id": alert.id,
            "reason": reason,
        }

    def _proposal_evidence(self, proposal):
        previous = proposal.previous_line_id.with_env(self.env)
        finding = proposal.finding_id.with_env(self.env)
        alert = proposal.alert_id.with_env(self.env)
        for record in (previous, previous.repair_id, finding, finding.revision_id, alert):
            if record:
                record.check_access("read")
        if not (previous or finding or alert):
            raise UserError(_("La propuesta ya no tiene evidencia disponible."))
        return {
            "previous_line_id": previous.id,
            "finding_id": finding.id,
            "alert_id": alert.id,
            "reason": proposal.reason,
        }

    def _record_classification(self, line, kind, previous, reason):
        line._check_rework_access()
        lock_source(line.repair_id)
        lock_source(line)
        line._check_rework_access()
        current = self._latest(line).get(line.id)
        if current and current.state == "rework":
            raise UserError(_("El retrabajo ya fue confirmado."))
        if kind not in dict(KINDS):
            raise UserError(_("Seleccione una clasificación válida."))
        if kind != "rework":
            if not current or current.state != kind:
                self._append(line, kind)
            return
        evidence = self._evidence_for(line, previous, reason)
        self._append(line, "proposal", **evidence)

    def _confirm_classification(self, line, proposal_id):
        line._check_rework_access(supervisor=True)
        lock_source(line.repair_id)
        lock_source(line)
        line._check_rework_access(supervisor=True)
        current = self._latest(line).get(line.id)
        if not current:
            raise UserError(_("Abra una propuesta vigente antes de confirmar."))
        if current.state == "rework" and current.proposal_id.id == proposal_id:
            return
        if current.state != "proposal" or current.id != proposal_id:
            raise UserError(_("La propuesta cambió. Vuelva a abrirla antes de confirmar."))
        self._append(line, "rework", proposal_id=current.id, **self._proposal_evidence(current))


class RepairWorkLineRework(models.Model):
    """Presenta las acciones de clasificación en Cierre de Reparación."""

    _inherit = "mc.rov.linea.falla"

    mc_rework_state = fields.Selection(
        [("pending", "Sin clasificar"), *STATES],
        compute="_compute_mc_rework_state",
        string="Clasificación Q3",
    )

    @api.depends_context("uid", "company")
    def _compute_mc_rework_state(self):
        readable = self.filtered(
            lambda line: line.id
            and line.repair_id.has_access("read")
            and line.repair_id.lot_id.has_access("read")
        )
        latest = self.env["mc.rov.repair.rework.event"]._latest(readable)
        for line in self:
            event = latest.get(line.id)
            line.mc_rework_state = event.state if event else "pending"

    def _check_rework_access(self, *, supervisor=False):
        self.ensure_one()
        group = SUPERVISOR if supervisor else "stock.group_stock_user"
        if self.env.user.share or not self.env.user.has_group(group):
            raise AccessError(_("Se requiere el permiso correspondiente en Reparación."))
        self.check_access("read")
        self.check_access("write")
        repair = self.repair_id
        repair.check_access("read")
        repair.check_access("write")
        repair.lot_id.check_access("read")
        if repair.company_id not in self.env.companies:
            raise AccessError(_("La orden pertenece a otra empresa."))
        if repair.state == "cancel" or not repair.lot_id.es_un_rov:
            raise UserError(_("La clasificación requiere una visita ROV vigente."))

    def _open_rework(self, *, supervisor=False):
        self._check_rework_access(supervisor=supervisor)
        defaults = {"default_line_id": self.id, "default_review": supervisor}
        if supervisor:
            ledger = self.env["mc.rov.repair.rework.event"]
            proposal = ledger._latest(self).get(self.id)
            if not proposal or proposal.state != "proposal":
                raise UserError(_("Seleccione una propuesta de retrabajo pendiente."))
            evidence = ledger._proposal_evidence(proposal)
            defaults.update(
                {
                    "default_proposal_id": proposal.id,
                    "default_kind": "rework",
                    **{f"default_{key}": value for key, value in evidence.items()},
                }
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Confirmar retrabajo") if supervisor else _("Clasificar trabajo"),
            "res_model": "mc.rov.repair.rework.wizard",
            "views": [(self.env.ref("mc_rov.view_repair_rework_wizard").id, "form")],
            "target": "new",
            "context": defaults,
        }

    def action_mc_propose_rework(self):
        return self._open_rework()

    def action_mc_confirm_rework(self):
        return self._open_rework(supervisor=True)
