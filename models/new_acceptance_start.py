"""Open formal RND/TRN attempts independently of reminder configuration."""

# The hook and standalone checker load different pylint-odoo rule catalogs.
# pylint: disable=unknown-option-value

import hashlib
import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import SQL


_CAPTURE = object()
_CAPTURE_KEY = "mc_new_acceptance_capability"


def _check_capability(records):
    if not records.env.su or records.env.context.get(_CAPTURE_KEY) is not _CAPTURE:
        raise UserError(_("El intento se registra desde la aceptación formal validada."))


def _lock_rows(env, table, ids):
    # A no-op UPDATE also serializes a transaction whose old snapshot saw no attempt.
    for identity in sorted(set(ids)):
        env.cr.execute(
            SQL(
                "UPDATE %s SET write_date=write_date WHERE id=%s",
                SQL.identifier(table),
                identity,
            )
        )


class NewAcceptanceEpisode(models.Model):
    """One new unit, retaining its real manufacturing origin through administrative splits."""

    _name = "mc.rov.new.acceptance.episode"
    _description = "Aceptación formal de equipo nuevo"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    lot_id = fields.Many2one("stock.lot", required=True, ondelete="restrict", check_company=True)
    product_id = fields.Many2one(
        "product.product", required=True, ondelete="restrict", check_company=True
    )
    production_id = fields.Many2one(
        "mrp.production", required=True, ondelete="restrict", check_company=True
    )
    production_group_id = fields.Many2one(
        "mrp.production.group", required=True, ondelete="restrict"
    )
    started_at = fields.Datetime(required=True)
    _unit_unique = models.Constraint(
        "UNIQUE(company_id, lot_id)", "La unidad nueva ya tiene un episodio de aceptación."
    )

    @api.model_create_multi
    def create(self, vals_list):
        _check_capability(self)
        return super().create(vals_list)

    def write(self, values):
        # Immutable identities deliberately have no underlying write gateway.
        # pylint: disable=method-required-super
        _check_capability(self)
        raise UserError(_("El episodio conserva la identidad de la unidad fabricada."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_formal_identity(self):
        raise UserError(_("La identidad de aceptación formal no se puede borrar."))


class NewAcceptanceAttempt(models.Model):
    """Private joint scope; stage outcomes will be captured by the native event increment."""

    _name = "mc.rov.new.acceptance.attempt"
    _description = "Intento conjunto de aceptación de equipo nuevo"
    _order = "episode_id, ordinal, id"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    episode_id = fields.Many2one(
        "mc.rov.new.acceptance.episode", required=True, ondelete="restrict", check_company=True
    )
    rnd_id = fields.Many2one("mc.rov.revision", required=True, ondelete="restrict")
    trn_id = fields.Many2one("mc.rov.revision", required=True, ondelete="restrict")
    ordinal = fields.Integer(required=True)
    state = fields.Selection(
        [("pending", "Pendiente"), ("confirmed", "Confirmado"), ("failed", "Fallido")],
        required=True,
        default="pending",
    )
    started_at = fields.Datetime(required=True)
    actor_id = fields.Many2one("res.users", required=True, ondelete="restrict")
    requirements_snapshot = fields.Json(required=True)
    configuration_digest = fields.Char(required=True)
    _ordinal_unique = models.Constraint(
        "UNIQUE(episode_id, ordinal)", "El ordinal de este intento ya existe."
    )
    _positive_ordinal = models.Constraint("CHECK(ordinal > 0)", "El ordinal debe ser positivo.")

    @api.model_create_multi
    def create(self, vals_list):
        _check_capability(self)
        return super().create(vals_list)

    def write(self, values):
        _check_capability(self)
        if set(values) - {
            "state",
            "closed_at",
            "finished_by_id",
            "first_pass_snapshot",
            "requirements_snapshot",
        } or any(row.state != "pending" for row in self):
            raise UserError(_("El intento conserva su identidad y evidencia cerrada."))
        for row in self:
            snapshot = values.get("requirements_snapshot", row.requirements_snapshot)
            if snapshot.get("configuration") != row.requirements_snapshot.get("configuration"):
                raise UserError(_("El alcance original no puede sustituirse."))
            previous = row.requirements_snapshot.get("results", {})
            if any(
                snapshot.get("results", {}).get(key) != value for key, value in previous.items()
            ):
                raise UserError(_("El resultado capturado de una prueba no puede sustituirse."))
        return super().write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_formal_attempt(self):
        raise UserError(_("El intento formal no se puede borrar."))


class NewAcceptanceService(models.AbstractModel):
    """Authorize real produced serials and explicit draft evidence before private writes."""

    _name = "mc.rov.new.acceptance"
    _description = "Servicio de aceptación conjunta de equipo nuevo"

    def _sources(self, production_id, lot_id, rnd_id, trn_id):
        if self.env.user.share or self.env.user._is_public():
            raise AccessError(_("La aceptación requiere una cuenta interna."))
        identities = (production_id, lot_id, rnd_id, trn_id)
        if any(not isinstance(i, int) or isinstance(i, bool) or i <= 0 for i in identities):
            raise ValidationError(_("Seleccione documentos guardados e identificadores válidos."))
        production = self.env["mrp.production"].browse(production_id)
        lot = self.env["stock.lot"].browse(lot_id)
        rnd = self.env["mc.rov.revision"].browse(rnd_id)
        trn = self.env["mc.rov.revision"].browse(trn_id)
        for record in (production, lot, rnd, trn):
            if not record.exists():
                raise ValidationError(_("Uno de los documentos seleccionados ya no existe."))
            record.check_access("read")
            record.check_access("write")
        return production, lot, rnd, trn

    def _validate_sources(self, production, lot, rnd, trn):
        companies = self.env.companies.ids
        if production.company_id.id not in companies or (
            lot.company_id and lot.company_id != production.company_id
        ):
            raise AccessError(_("La unidad no pertenece a una empresa activa autorizada."))
        production.product_id.check_access("read")
        if production.state != "done" or lot not in self.env[
            "mc.rov.acceptance.activity.automation"
        ]._produced_lots(production):
            raise UserError(
                _("Seleccione una serie realmente producida en una fabricación terminada.")
            )
        if not production.production_group_id:
            raise UserError(_("La fabricación debe conservar su grupo de origen nativo."))
        for revision, kind in ((rnd, "rendimiento"), (trn, "terreno")):
            if revision.tipo != kind or revision.lot_id != lot or revision.repair_id:
                raise ValidationError(
                    _("Seleccione rendimiento y terreno de esta unidad, sin reparación.")
                )
            if revision.estado != "borrador" or revision.documento_emitido:
                raise UserError(
                    _(
                        "Seleccione pruebas nuevas sin confirmar; el intento se inicia antes de sus resultados."
                    )
                )

    @api.model
    def start_attempt(self, production_id, lot_id, rnd_id, trn_id):
        # Keep authorization, identity resolution and capture in one atomic boundary.
        # pylint: disable=too-many-locals
        with self.env.cr.savepoint():
            sources = self._sources(production_id, lot_id, rnd_id, trn_id)
            production, lot, rnd, trn = sources
            _lock_rows(self.env, "mrp_production", production.ids)
            _lock_rows(self.env, "stock_lot", lot.ids)
            _lock_rows(self.env, "mc_rov_revision", (rnd | trn).ids)
            for record in sources:
                record.invalidate_recordset()
                record.check_access("write")
            self._validate_sources(*sources)
            episodes = self.env["mc.rov.new.acceptance.episode"].sudo()
            episode = episodes.search(
                [("company_id", "=", production.company_id.id), ("lot_id", "=", lot.id)]
            )
            if episode and (
                episode.product_id.id != production.product_id.id
                or episode.production_group_id.id != production.production_group_id.id
            ):
                raise UserError(_("La serie ya tiene una aceptación de otro origen fabricado."))
            if not episode:
                episode = episodes.with_context(**{_CAPTURE_KEY: _CAPTURE}).create(
                    {
                        "company_id": production.company_id.id,
                        "product_id": production.product_id.id,
                        "production_id": production.id,
                        "production_group_id": production.production_group_id.id,
                        "lot_id": lot.id,
                        "started_at": fields.Datetime.now(),
                    }
                )
            attempts = (
                self.env["mc.rov.new.acceptance.attempt"]
                .sudo()
                .search([("episode_id", "=", episode.id)], order="ordinal")
            )
            pending = attempts.filtered(lambda row: row.state == "pending")
            if pending:
                if len(pending) != 1 or pending.rnd_id.id != rnd.id or pending.trn_id.id != trn.id:
                    raise UserError(
                        _("La unidad ya tiene un intento pendiente con otras pruebas.")
                    )
                return True
            # A source belongs to one attempt, so reusing a later edited revision
            # cannot replace the evidence of an earlier formal presentation.
            if (
                self.env["mc.rov.new.acceptance.attempt"]
                .sudo()
                .search_count(["|", ("rnd_id", "=", rnd.id), ("trn_id", "=", trn.id)])
            ):
                raise UserError(_("Utilice pruebas nuevas para el siguiente intento formal."))
            configuration = {
                "performance": rnd._acceptance_configuration()[0],
                "field": trn._acceptance_configuration()[0],
            }
            digest = hashlib.sha256(
                json.dumps(configuration, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()
            self.env["mc.rov.new.acceptance.attempt"].sudo().with_context(
                **{_CAPTURE_KEY: _CAPTURE}
            ).create(
                {
                    "company_id": production.company_id.id,
                    "episode_id": episode.id,
                    "rnd_id": rnd.id,
                    "trn_id": trn.id,
                    "ordinal": max(attempts.mapped("ordinal"), default=0) + 1,
                    "state": "pending",
                    "started_at": fields.Datetime.now(),
                    "actor_id": self.env.uid,
                    "requirements_snapshot": {"configuration": configuration},
                    "configuration_digest": digest,
                }
            )
        return True


class NewAcceptanceRevision(models.Model):
    """Protect selected source identities and membership while preserving editable answers."""

    _inherit = "mc.rov.revision"

    def _new_acceptance_followed(self):
        self.check_access("write")
        attempts = (
            self.env["mc.rov.new.acceptance.attempt"]
            .sudo()
            .search(["|", ("rnd_id", "in", self.ids), ("trn_id", "in", self.ids)])
        )
        if any(row.company_id.id not in self.env.companies.ids for row in attempts):
            raise AccessError(_("La aceptación no pertenece a una empresa activa autorizada."))
        episodes = attempts.episode_id
        _lock_rows(self.env, "mrp_production", episodes.production_id.ids)
        _lock_rows(self.env, "stock_lot", episodes.lot_id.ids)
        _lock_rows(self.env, "mc_rov_revision", self.ids)
        self.invalidate_recordset()
        attempts.invalidate_recordset()
        return attempts

    def _check_final_acceptance_scope_edit(self):
        followed = self._new_acceptance_followed()
        if followed.filtered(lambda row: row.state == "pending"):
            raise UserError(_("Las filas y componentes pertenecen al intento conjunto pendiente."))
        return super()._check_final_acceptance_scope_edit()

    def write(self, values):
        identity = {"tipo", "lot_id", "repair_id", "mc_acceptance_purpose"}.intersection(values)
        if identity:
            followed = self._new_acceptance_followed()
            for revision in self:
                if followed.filtered(
                    lambda row, rev=revision: rev.id in (row.rnd_id.id, row.trn_id.id)
                ):
                    for name in identity:
                        current = revision[name]
                        if revision._fields[name].type == "many2one":
                            current = current.id
                        if current != values[name]:
                            raise UserError(
                                _("La prueba conserva su identidad de aceptación conjunta.")
                            )
        return super().write(values)


class NewAcceptanceLot(models.Model):
    """A registered new unit cannot silently become another product or company."""

    _inherit = "stock.lot"

    def write(self, values):
        identity = {"product_id", "company_id"}.intersection(values)
        if identity:
            self.check_access("write")
            episodes = (
                self.env["mc.rov.new.acceptance.episode"]
                .sudo()
                .search([("lot_id", "in", self.ids)])
            )
            _lock_rows(self.env, "mrp_production", episodes.production_id.ids)
            _lock_rows(self.env, "stock_lot", self.ids)
            self.invalidate_recordset(list(identity))
            for lot in self:
                if episodes.filtered(lambda row, source=lot: row.lot_id.id == source.id) and any(
                    lot[name].id != (values[name] or False) for name in identity
                ):
                    raise UserError(_("La serie conserva producto y empresa de su aceptación."))
        return super().write(values)


class NewAcceptanceProduction(models.Model):
    """Preserve captured manufacturing provenance, without preventing native reversals."""

    _inherit = "mrp.production"

    def write(self, values):
        identity = {"product_id", "company_id", "production_group_id"}.intersection(values)
        if identity:
            self.check_access("write")
            _lock_rows(self.env, "mrp_production", self.ids)
            self.invalidate_recordset(list(identity))
            episodes = (
                self.env["mc.rov.new.acceptance.episode"]
                .sudo()
                .search([("production_id", "in", self.ids)])
            )
            for production in self:
                if episodes.filtered(
                    lambda row, source=production: row.production_id.id == source.id
                ) and any(production[name].id != (values[name] or False) for name in identity):
                    raise UserError(
                        _("La fabricación conserva el origen de su aceptación formal.")
                    )
        return super().write(values)
