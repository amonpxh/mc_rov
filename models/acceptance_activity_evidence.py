from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import SQL


class AcceptanceActivityEvidence(models.AbstractModel):
    """Elige evidencia explícita sin convertir una revisión reciente en aceptación."""

    _inherit = "mc.rov.acceptance.activity.automation"

    def _cycle_for_lot(self, lot, write=True, lock=True):
        actor = self.with_user(self.env.uid)
        if not actor.env.user.has_group("base.group_user"):
            raise AccessError(_("Este acceso requiere una cuenta interna."))
        if lot._name != "stock.lot" or not isinstance(lot.id, int) or lot.id <= 0:
            raise UserError(_("Guarde el equipo antes de seleccionar su aceptación."))
        lot = actor.env["stock.lot"].browse(lot.id).exists()
        if not lot:
            raise UserError(_("El equipo ya no existe."))
        lot.check_access("write" if write else "read")
        lot.check_access("read")
        companies = actor.env.companies.ids
        if lot.company_id and lot.company_id.id not in companies:
            raise AccessError(_("El equipo pertenece a otra empresa activa."))
        cycles = (
            actor.env["mc.rov.acceptance.activity.cycle"]
            .sudo()
            .search(
                [("lot_id", "=", lot.id), ("state", "=", "open"), ("company_id", "in", companies)]
            )
        )
        if len(cycles) != 1:
            raise UserError(
                _("El equipo debe tener una única aceptación abierta para elegir pruebas.")
            )
        if lot.company_id and lot.company_id != cycles.company_id:
            raise ValidationError(_("El equipo ya no corresponde a la empresa de su aceptación."))
        if lock:
            # Mantener el orden MO -> lote -> ciclo usado al generar los pendientes.
            actor.env.cr.execute(
                SQL(
                    "SELECT id FROM mrp_production WHERE id = %s FOR UPDATE",
                    cycles.production_id.id,
                )
            )
            actor.env.cr.execute(SQL("SELECT id FROM stock_lot WHERE id = %s FOR UPDATE", lot.id))
            actor.env.cr.execute(
                SQL(
                    "SELECT id FROM mc_rov_acceptance_activity_cycle WHERE id = %s FOR UPDATE",
                    cycles.id,
                )
            )
            cycles.invalidate_recordset(["state", "rnd_id", "trn_id", "lot_id", "company_id"])
            if cycles.state != "open" or cycles.lot_id.id != lot.id:
                raise UserError(_("La aceptación cambió; vuelva a abrir la selección de pruebas."))
        return cycles

    def _readable_revision(self, revision):
        model = self.env["mc.rov.revision"].with_user(self.env.uid)
        if not revision:
            return model.browse()
        if revision._name != model._name or not isinstance(revision.id, int) or revision.id <= 0:
            raise ValidationError(_("Seleccione una prueba guardada."))
        record = model.browse(revision.id).exists()
        if not record:
            raise ValidationError(_("La prueba seleccionada ya no existe."))
        record.check_access("read")
        return record

    def _evidence_summary(self, lot):
        cycle = self._cycle_for_lot(lot, write=False, lock=False)
        rnd = self._readable_revision(cycle.rnd_id)
        trn = self._readable_revision(cycle.trn_id)
        return {
            "rnd_id": rnd.id or False,
            "trn_id": trn.id or False,
            "summary": _("Seleccione las pruebas de este equipo para su aceptación abierta."),
        }

    def _select_evidence(self, lot, rnd=None, trn=None, reason=False):
        with self.env.cr.savepoint():
            cycle = self._cycle_for_lot(lot)
            self._readable_revision(cycle.rnd_id)
            self._readable_revision(cycle.trn_id)
            changes = []
            motive = (reason or "").strip()
            for field, stage, kind, value in (
                ("rnd_id", "performance", "rendimiento", rnd),
                ("trn_id", "field", "terreno", trn),
            ):
                if value is None:
                    continue
                candidate = self._readable_revision(value)
                if candidate and (
                    candidate.lot_id.id != lot.id or candidate.tipo != kind or candidate.repair_id
                ):
                    raise ValidationError(
                        _(
                            "Seleccione una prueba del tipo y equipo correctos, sin orden de reparación."
                        )
                    )
                old = self._readable_revision(cycle[field])
                if old == candidate:
                    continue
                if old and not motive:
                    raise ValidationError(
                        _("Indique un motivo para reemplazar o retirar una prueba.")
                    )
                if candidate and self.env["mc.rov.acceptance.activity.cycle"].sudo().search_count(
                    [(field, "=", candidate.id), ("id", "!=", cycle.id)]
                ):
                    raise ValidationError(_("La prueba ya acredita otro ciclo de aceptación."))
                changes.append((field, stage, old, candidate))
            if not changes:
                return
            cycle.write(
                {field: candidate.id or False for field, _stage, _old, candidate in changes}
            )
            self._record_evidence_selection(cycle, changes, motive)
            self._after_evidence_selection(
                self.env["stock.lot"].with_user(self.env.uid).browse(lot.id)
            )

    def _record_evidence_selection(self, cycle, changes, motive):
        instant = fields.Datetime.now()
        history = self.env["mc.rov.acceptance.evidence.history"].sudo()
        actor_lot = self.env["stock.lot"].with_user(self.env.uid).browse(cycle.lot_id.id)
        for _field, stage, old, candidate in changes:
            history.create(
                {
                    "company_id": cycle.company_id.id,
                    "cycle_id": cycle.id,
                    "stage": stage,
                    "revision_id": candidate.id or False,
                    "previous_revision_id": old.id or False,
                    "actor_id": self.env.uid,
                    "selected_at": instant,
                    "reason": motive or False,
                }
            )
            actor_lot.message_post(
                body=Markup("<p>%s: %s → %s. %s</p>")
                % (
                    _("Evidencia de aceptación"),
                    old.display_name or _("Sin selección"),
                    candidate.display_name or _("Sin selección"),
                    motive or _("Selección inicial"),
                )
            )

    def _after_evidence_selection(self, lot):
        """Punto de extensión para reconciliar resultados sin mezclar selección y emisión."""

    def _create_evidence(self, lot, kind, reason=False):
        if kind not in ("rendimiento", "terreno"):
            raise ValidationError(_("Elija una prueba de rendimiento o terreno."))
        with self.env.cr.savepoint():
            self._cycle_for_lot(lot)
            # Los defaults RPC de otro formulario no pueden confirmar o ligar una reparación.
            context = {
                key: value
                for key, value in self.env.context.items()
                if not key.startswith("default_")
            }
            revision = (
                self.env["mc.rov.revision"]
                .with_user(self.env.uid)
                .with_context(context)
                .create({"lot_id": lot.id, "tipo": kind, "estado": "borrador", "repair_id": False})
            )
            self._select_evidence(
                lot, **{"rnd" if kind == "rendimiento" else "trn": revision}, reason=reason
            )
        return revision


class AcceptanceEvidenceLot(models.Model):
    """Acceso nativo desde el equipo sin exponer claves del historial privado."""

    _inherit = "stock.lot"

    def action_mc_acceptance_evidence(self):
        self.ensure_one()
        self.env["mc.rov.acceptance.activity.automation"]._cycle_for_lot(self)
        return {
            "type": "ir.actions.act_window",
            "name": _("Pruebas de aceptación"),
            "res_model": "mc.rov.acceptance.evidence.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_lot_id": self.id, "allowed_company_ids": self.env.companies.ids},
        }
