"""Constancia explícita de la salida efectiva para los compromisos al cliente."""

# Los catálogos pylint-odoo del proyecto difieren en method-required-super.
# pylint: disable=unknown-option-value

import hashlib

from markupsafe import Markup

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import format_date, format_datetime

from .production_kpi_event import lock_source
from .production_kpi_metrics import local_day


_APPEND_DISPATCH = object()

DISPATCH_KINDS = [
    ("confirmed", "Confirmación"),
    ("corrected", "Corrección"),
    ("invalidated", "Invalidación"),
]
DISPATCH_MODES = [("dispatch", "Despacho"), ("pickup", "Retiro")]


class CustomerDispatch(models.Model):
    """Conserva cada constancia de salida y la secuencia de sus correcciones.

    El último id por transferencia determina la evidencia vigente. Confirmación y
    corrección aportan una fecha efectiva. Invalidación conserva la evidencia que
    retiró y deja la transferencia sin fecha evaluable hasta nueva corrección.
    """

    _name = "mc.rov.customer.dispatch"
    _description = "Constancia de salida ROV al cliente"
    _check_company_auto = True
    _order = "id desc"
    _rec_name = "picking_id"

    picking_id = fields.Many2one(
        "stock.picking", required=True, ondelete="restrict", index=True, check_company=True
    )
    company_id = fields.Many2one("res.company", required=True, ondelete="restrict", index=True)
    actor_id = fields.Many2one(
        "res.users", string="Registrado por", required=True, ondelete="restrict"
    )
    previous_id = fields.Many2one(
        "mc.rov.customer.dispatch", ondelete="restrict", check_company=True
    )
    # Un despacho puede contener varias visitas, cada una asociada a una serie distinta.
    repair_ids = fields.Many2many(
        "repair.order",
        relation="mc_rov_customer_dispatch_repair_rel",
        string="Visitas de reparación",
        check_company=True,
    )
    attachment_id = fields.Many2one(
        "ir.attachment", string="Constancia", required=True, ondelete="restrict"
    )
    attachment_fingerprint = fields.Char(string="Huella de la constancia", required=True)
    kind = fields.Selection(DISPATCH_KINDS, string="Acción", required=True)
    mode = fields.Selection(DISPATCH_MODES, string="Modalidad", required=True)
    effective_date = fields.Date(string="Día de salida")
    effective_at = fields.Datetime(string="Fecha y hora de salida")
    reason = fields.Text(string="Motivo")

    _effective_precision = models.Constraint(
        "CHECK ((effective_date IS NULL) <> (effective_at IS NULL))",
        "La salida debe tener un día o una fecha y hora, según la precisión de la constancia.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su or self.env.context.get("_mc_dispatch_append") is not _APPEND_DISPATCH:
            raise AccessError(_("Registre la constancia desde la transferencia."))
        return super().create(vals_list)

    def write(self, vals):
        # pylint: disable=method-required-super
        raise AccessError(_("Corrija la constancia mediante un nuevo evento."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        raise AccessError(_("Invalide la constancia mediante un nuevo evento."))

    def _readable_attachment(self, picking):
        """Aplica permisos nativos al respaldo antes de mostrar el nombre o enlace."""
        self.ensure_one()
        attachment = self.attachment_id.with_env(picking.env)
        if self.picking_id.id == picking.id and self._attachment_belongs_to(attachment, picking):
            return attachment
        return attachment.browse()

    def _can_read_linked_repairs(self, env):
        repairs = self.repair_ids.with_env(env)
        return not repairs or repairs.has_access("read")

    @api.model
    def _attachment_fingerprint(self, attachment):
        # Inventario permite reemplazar el adjunto. Se sella el checksum nativo
        # o la URL para detectar cambios sin volver a cargar el archivo.
        content = attachment.url if attachment.type == "url" else attachment.checksum
        if not content:
            return False
        return hashlib.sha256(f"{attachment.type}:{content}".encode()).hexdigest()

    def _matching_attachment(self, picking):
        """Contrasta la huella con el adjunto visible en el entorno de la transferencia."""
        attachment = self._readable_attachment(picking)
        if attachment and self.attachment_fingerprint == self._attachment_fingerprint(attachment):
            return attachment
        return attachment.browse()

    def _evidence_matches(self, picking):
        return bool(self._matching_attachment(picking))

    @api.model
    def _attachment_belongs_to(self, attachment, picking):
        return (
            attachment
            and attachment.has_access("read")
            and attachment.res_model == "stock.picking"
            and attachment.res_id == picking.id
            and (not attachment.res_field or attachment.res_field == "signature")
        )

    def _wizard_evidence(self, wizard, picking):
        attachment = wizard.attachment_id.exists()
        fingerprint = self._attachment_belongs_to(
            attachment, picking
        ) and self._attachment_fingerprint(attachment)
        if not fingerprint:
            raise ValidationError(_("Seleccione una constancia accesible de esta transferencia."))
        effective_date = wizard.effective_date if wizard.precision == "date" else False
        effective_at = wizard.effective_at if wizard.precision == "datetime" else False
        if not wizard.mode or not (effective_date or effective_at):
            raise ValidationError(_("Ingrese modalidad y fecha efectiva de salida."))
        now = fields.Datetime.now()
        if (effective_date and effective_date > local_day(now)) or (
            effective_at and effective_at > now
        ):
            raise ValidationError(_("La salida efectiva no puede ser futura."))
        repairs = wizard.repair_ids
        if repairs:
            repairs.check_access("read")
            domain = [("id", "in", repairs.ids), *picking._dispatch_repair_domain()]
            valid_visits = repairs.search_count(domain)
            if valid_visits != len(repairs) or len(repairs.lot_id) != len(repairs):
                raise ValidationError(
                    _("Seleccione una sola visita del cliente por cada serie ROV entregada.")
                )
        return {
            "attachment_id": attachment.id,
            "attachment_fingerprint": fingerprint,
            "repair_ids": [Command.set(repairs.ids)],
            "mode": wizard.mode,
            "effective_date": effective_date,
            "effective_at": effective_at,
        }

    @api.model
    def _append_from_wizard(self, wizard):
        picking = wizard.picking_id
        picking._check_dispatch_capture()
        # En REPEATABLE READ, el bloqueo con escritura fuerza el reintento de
        # quien abrió el mismo borrador antes de la primera constancia.
        lock_source(picking)
        picking._check_dispatch_capture()
        ledger = self.sudo().with_context({}, _mc_dispatch_append=_APPEND_DISPATCH)
        latest = ledger.search([("picking_id", "=", picking.id)], limit=1)
        if (latest.id or 0) != wizard.expected_event_id:
            raise UserError(_("La constancia cambió. Cierre y vuelva a abrir el asistente."))
        if not latest._can_read_linked_repairs(self.env):
            raise AccessError(_("La constancia requiere lectura de las visitas vinculadas."))
        kind = wizard.kind
        if (kind == "confirmed" and latest) or (kind != "confirmed" and not latest):
            raise UserError(_("Abra el asistente correspondiente a la constancia vigente."))
        reason = (wizard.reason or "").strip()
        if kind != "confirmed" and not reason:
            raise ValidationError(_("Ingrese el motivo de la corrección o invalidación."))
        if kind == "invalidated":
            if latest.kind == kind:
                raise UserError(_("La constancia ya está invalidada."))
            evidence = {
                "attachment_id": latest.attachment_id.id,
                "attachment_fingerprint": latest.attachment_fingerprint,
                "repair_ids": [Command.set(latest.repair_ids.ids)],
                "mode": latest.mode,
                "effective_date": latest.effective_date,
                "effective_at": latest.effective_at,
            }
        else:
            evidence = self._wizard_evidence(wizard, picking)
        return ledger.create(
            {
                **evidence,
                "picking_id": picking.id,
                "company_id": picking.company_id.id,
                "actor_id": self.env.uid,
                "previous_id": latest.id,
                "kind": kind,
                "reason": reason or False,
            }
        )


class RepairOrderCustomerDispatch(models.Model):
    """Conserva las visitas referenciadas por el historial de salida."""

    _inherit = "repair.order"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_dispatch_history(self):
        # Las relaciones M2M nativas se eliminan en cascada sin este control.
        if (
            self.env["mc.rov.customer.dispatch"]
            .sudo()
            .search_count([("repair_ids", "in", self.ids)], limit=1)
        ):
            raise UserError(_("La visita tiene una constancia de salida en su historial."))


class StockPickingCustomerDispatch(models.Model):
    """Expone constancias autorizadas en la transferencia nativa del taller."""

    _inherit = "stock.picking"

    mc_dispatch_visible = fields.Boolean(compute="_compute_customer_dispatch")
    mc_dispatch_can_capture = fields.Boolean(compute="_compute_customer_dispatch")
    mc_dispatch_can_invalidate = fields.Boolean(compute="_compute_customer_dispatch")
    mc_dispatch_history = fields.Html(
        string="Historial de constancias", compute="_compute_customer_dispatch"
    )

    def _is_dispatch_supervisor(self):
        user = self.env.user
        return (
            not user.share
            and user.has_group("base.group_user")
            and user.has_group("mc_rov.group_customer_commitment_supervisor")
        )

    def _customer_dispatch_eligible(self):
        self.ensure_one()
        if self.state != "done":
            return False
        outward = self._customer_dispatch_outward_moves()
        root = self.env["stock.lot"]._get_rov_root_category()
        if not outward or not root:
            return False
        return bool(
            self.env["product.category"].search_count(
                [("id", "in", outward.product_id.categ_id.ids), ("id", "child_of", root.id)],
                limit=1,
            )
        )

    def _customer_dispatch_outward_moves(self):
        return self.move_ids.filtered(
            lambda move: move.state == "done"
            and move.location_id.usage == "internal"
            and move.location_dest_id.usage == "customer"
            and move.quantity > 0
        )

    def _dispatch_repair_domain(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        if not partner:
            return [("id", "=", False)]
        lines = self._customer_dispatch_outward_moves().move_line_ids.filtered(
            lambda line: line.quantity > 0
            and line.location_id.usage == "internal"
            and line.location_dest_id.usage == "customer"
            and line.lot_id.es_un_rov
        )
        return [
            ("lot_id", "in", lines.lot_id.ids),
            ("company_id", "=", self.company_id.id),
            ("partner_id.commercial_partner_id", "=", partner.id),
        ]

    def _check_dispatch_capture(self):
        self.ensure_one()
        if (
            not self._is_dispatch_supervisor()
            or not self.exists()
            or not self.has_access("read")
            or not self.has_access("write")
            or self.company_id not in self.env.companies
        ):
            raise AccessError(
                _("La constancia requiere supervisión y escritura en esta transferencia.")
            )
        if not self._customer_dispatch_eligible():
            raise UserError(
                _("Seleccione una transferencia validada con salida de un ROV al cliente.")
            )

    def _open_customer_dispatch_wizard(self, invalidate=False):
        self._check_dispatch_capture()
        latest = (
            self.env["mc.rov.customer.dispatch"]
            .sudo()
            .search([("picking_id", "=", self.id)], limit=1)
        )
        if not latest._can_read_linked_repairs(self.env):
            raise AccessError(_("La constancia requiere lectura de las visitas vinculadas."))
        if invalidate and (not latest or latest.kind == "invalidated"):
            raise UserError(_("La transferencia no tiene una constancia vigente para invalidar."))
        kind = "invalidated" if invalidate else ("corrected" if latest else "confirmed")
        values = {"picking_id": self.id, "expected_event_id": latest.id or 0, "kind": kind}
        if kind == "corrected":
            values.update(
                {
                    "repair_ids": [Command.set(latest.repair_ids.ids)],
                    "attachment_id": latest._readable_attachment(self).id,
                    "mode": latest.mode,
                    "precision": "date" if latest.effective_date else "datetime",
                    "effective_date": latest.effective_date,
                    "effective_at": latest.effective_at,
                }
            )
        wizard = self.env["mc.rov.customer.dispatch.wizard"].with_context({}).create(values)
        return {
            "type": "ir.actions.act_window",
            "name": {
                "confirmed": _("Registrar constancia de salida"),
                "corrected": _("Corregir constancia de salida"),
                "invalidated": _("Invalidar constancia de salida"),
            }[kind],
            "res_model": wizard._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "views": [(self.env.ref("mc_rov.customer_dispatch_wizard_form").id, "form")],
            "target": "new",
        }

    def action_open_customer_dispatch(self):
        return self._open_customer_dispatch_wizard()

    def action_open_customer_dispatch_invalidation(self):
        return self._open_customer_dispatch_wizard(invalidate=True)

    @api.depends_context("uid", "company", "lang", "tz")
    @api.depends(
        "state",
        "move_ids.state",
        "move_ids.quantity",
        "move_ids.product_id.categ_id",
        "move_ids.location_id.usage",
        "move_ids.location_dest_id.usage",
    )
    def _compute_customer_dispatch(self):
        ledger = self.env["mc.rov.customer.dispatch"]
        authorized = self.filtered(
            lambda picking: picking.id
            and picking.has_access("read")
            and picking.company_id in self.env.companies
        )
        history = (
            ledger.sudo()
            .search([("picking_id", "in", authorized.ids)])
            .grouped(lambda row: row.picking_id.id)
        )
        supervisor = self._is_dispatch_supervisor()
        for picking in self:
            rows = history.get(picking.id, ledger)
            eligible = picking in authorized and picking._customer_dispatch_eligible()
            latest = rows[:1]
            capture = (
                eligible
                and supervisor
                and picking.has_access("write")
                and latest._can_read_linked_repairs(self.env)
            )
            picking.mc_dispatch_visible = bool(rows or eligible)
            picking.mc_dispatch_can_capture = capture
            picking.mc_dispatch_can_invalidate = capture and bool(
                latest and latest.kind != "invalidated"
            )
            picking.mc_dispatch_history = (
                picking._format_customer_dispatch(rows) if rows else False
            )

    def _format_customer_dispatch(self, rows):
        kind_labels = dict(rows._fields["kind"]._description_selection(self.env))
        mode_labels = dict(rows._fields["mode"]._description_selection(self.env))
        entries = []
        for row in rows:
            attachment = row._matching_attachment(self)
            link = (
                Markup('<a href="/web/content/{}?download=true">{}</a>').format(
                    attachment.id, attachment.name
                )
                if attachment
                else _("Constancia no disponible")
            )
            repairs = row.repair_ids.with_env(self.env).filtered(
                lambda repair: repair.has_access("read")
            )
            effective = (
                format_date(self.env, row.effective_date)
                if row.effective_date
                else format_datetime(self.env, row.effective_at, tz=self.env.user.tz)
            )
            cells = (
                kind_labels[row.kind],
                mode_labels[row.mode],
                effective,
                link,
                ", ".join(repairs.mapped("display_name")),
                row.actor_id.display_name,
                format_datetime(self.env, row.create_date, tz=self.env.user.tz),
                row.reason or "",
            )
            entries.append(
                Markup("<tr>{}</tr>").format(
                    Markup("").join(Markup("<td>{}</td>").format(cell) for cell in cells)
                )
            )
        headings = (
            _("Acción"),
            _("Modalidad"),
            _("Salida efectiva"),
            _("Constancia"),
            _("Reparaciones"),
            _("Registrado por"),
            _("Fecha de registro"),
            _("Motivo"),
        )
        table = Markup(
            '<div class="table-responsive"><table class="table table-sm">'
            "<thead><tr>{}</tr></thead><tbody>{}</tbody></table></div>"
        )
        return table.format(
            Markup("").join(Markup('<th scope="col">{}</th>').format(label) for label in headings),
            Markup("").join(entries),
        )
