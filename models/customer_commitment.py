"""Promesas F3 y cambios acordados, protegidos por el acceso a su origen."""

# Los catálogos pylint-odoo del proyecto difieren en method-required-super.
# pylint: disable=unknown-option-value

from math import isclose

from odoo import _, api, Command, fields, models
from odoo.exceptions import AccessError, UserError

from .production_kpi_event import lock_source


SUPERVISOR_GROUP = "mc_rov.group_customer_commitment_supervisor"
_CAPTURE = object()
_KEY = "mc_customer_commitment_capability"


def check_capture(env):
    """Exige una capacidad Python que ningún contexto de RPC puede proporcionar."""
    if not env.su or env.context.get(_KEY) is not _CAPTURE:
        raise AccessError(_("Registre el acuerdo desde su documento de origen."))


class CustomerCommitment(models.Model):
    """Conserva el compromiso original por línea de venta o visita de reparación."""

    _name = "mc.rov.customer.commitment"
    _description = "Compromiso original de entrega al cliente"
    _check_company_auto = True
    _order = "agreed_at, id"

    company_id = fields.Many2one("res.company", required=True, ondelete="restrict", index=True)
    sale_line_id = fields.Many2one(
        "sale.order.line", ondelete="restrict", check_company=True, index=True
    )
    # La visita sigue siendo parte del alcance aunque el origen sea una línea de servicio.
    repair_id = fields.Many2one(
        "repair.order", ondelete="restrict", check_company=True, index=True
    )
    product_id = fields.Many2one(
        "product.product", required=True, ondelete="restrict", check_company=True
    )
    lot_ids = fields.Many2many(
        "stock.lot", ondelete="restrict", check_company=True, string="Series pactadas"
    )
    quantity = fields.Integer(required=True, string="Unidades pactadas")
    promised_date = fields.Date(string="Día pactado")
    promised_at = fields.Datetime(string="Fecha y hora pactadas")
    agreed_at = fields.Datetime(required=True, string="Aceptado el")
    evidence = fields.Text(required=True, string="Referencia al respaldo")
    actor_id = fields.Many2one("res.users", required=True, ondelete="restrict")
    change_ids = fields.One2many("mc.rov.customer.commitment.change", "commitment_id")

    _scope = models.Constraint(
        "CHECK (sale_line_id IS NOT NULL OR repair_id IS NOT NULL)",
        "El compromiso requiere una línea de venta o una visita.",
    )
    _sale_line_unique = models.Constraint(
        "UNIQUE (sale_line_id)", "Ya existe un compromiso para esta línea de venta."
    )
    _repair_unique = models.Constraint(
        "UNIQUE (repair_id)", "Ya existe un compromiso para esta visita."
    )
    _quantity_positive = models.Constraint(
        "CHECK (quantity > 0)", "El compromiso requiere unidades positivas."
    )
    _one_deadline = models.Constraint(
        "CHECK ((promised_date IS NOT NULL) <> (promised_at IS NOT NULL))",
        "Registre el día pactado o la fecha y hora pactadas.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        check_capture(self.env)
        return super().create(vals_list)

    def write(self, vals):
        # pylint: disable=method-required-super
        raise AccessError(_("El compromiso original conserva los términos aceptados."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_history(self):
        raise AccessError(_("No se elimina la evidencia de compromisos."))

    def _commitment_source(self):
        """Devuelve el origen original aunque la reparación reciba un pedido después."""
        self.ensure_one()
        return self.sale_line_id.order_id or self.repair_id

    def _authorize_source(self, source, operation="read"):
        source.ensure_one()
        user = self.env.user
        if not user.has_group("base.group_user") or user.share:
            raise AccessError(_("Se requiere una cuenta interna autorizada."))
        if source._name not in {"sale.order", "repair.order"} or not source.exists():
            raise AccessError(_("El documento de origen no está disponible."))
        source.check_access(operation)
        if source.company_id not in self.env.companies:
            raise AccessError(_("El documento no pertenece a una empresa activa autorizada."))
        if operation == "write" and not user.has_group(SUPERVISOR_GROUP):
            raise AccessError(_("Se requiere el rol Supervisor de compromisos al cliente."))

    def _rows_for_source(self, source):
        self._authorize_source(source)
        ledger = self.sudo()
        if source._name == "repair.order":
            domain = [("repair_id", "=", source.id)]
        else:
            domain = [
                "|",
                ("sale_line_id.order_id", "=", source.id),
                "&",
                ("sale_line_id", "=", False),
                ("repair_id.sale_order_id", "=", source.id),
            ]
        rows = ledger.search([("company_id", "=", source.company_id.id), *domain])
        return rows.filtered(
            lambda row: row._commitment_source().with_env(self.env).has_access("read")
            and (not row.sale_line_id or row.sale_line_id.with_env(self.env).has_access("read"))
            and (not row.repair_id or row.repair_id.with_env(self.env).has_access("read"))
        )

    def _sale_visit(self, source, line):
        # Se considera la cardinalidad real antes de autorizar el registro encontrado.
        # Una visita oculta no debe permitir una segunda promesa por la misma línea.
        visits = (
            self.env["repair.order"].sudo().search([("sale_order_line_id", "=", line.id)], limit=2)
        )
        if len(visits) > 1:
            raise UserError(_("La línea de venta no identifica una única visita de reparación."))
        visit = visits.with_env(self.env)
        if visit:
            visit.check_access("read")
            lock_source(visit, access="read")
            if visit.sale_order_id != source or visit.company_id != source.company_id:
                raise UserError(_("Verifique el vínculo nativo entre el pedido y la visita."))
        elif line.product_id.type == "service":
            raise UserError(_("Vincule esta línea de servicio a una visita identificada."))
        return visit

    def _repair_scope(self, source, repair, lots):
        product = repair.product_id
        lot = repair.lot_id
        if lot:
            lot.check_access("read")
        if (
            not lot
            or product.tracking != "serial"
            or not lot.es_un_rov
            or lot.product_id != product
        ):
            raise UserError(_("Identifique la serie ROV de la visita para registrar su promesa."))
        if lots and lot != lots:
            raise UserError(_("La serie pactada debe coincidir con la serie de la visita."))
        if repair.company_id != source.company_id:
            raise AccessError(_("La visita debe pertenecer a la empresa del origen."))
        return product, lot, 1

    def _sale_product_scope(self, line, lots):
        product = line.product_id
        product.check_access("read")
        root = self.env["stock.lot"]._get_rov_root_category()
        if (
            product.tracking != "serial"
            or not root
            or not self.env["product.category"].search_count(
                [("id", "=", product.categ_id.id), ("id", "child_of", root.id)]
            )
        ):
            raise UserError(_("Seleccione una línea de venta de ROV con seguimiento por serie."))
        units = line.product_uom_id._compute_quantity(
            line.product_uom_qty, product.uom_id, round=False
        )
        quantity = round(units)
        if quantity <= 0 or not isclose(units, quantity, rel_tol=0, abs_tol=1e-8):
            raise UserError(_("La línea debe comprometer una cantidad entera de unidades ROV."))
        if len(lots) > quantity:
            raise UserError(_("Las series pactadas exceden las unidades de la línea."))
        return product, lots, quantity

    def _create_commitment(self, source, line, wizard, terms):
        if source.state == "cancel":
            raise UserError(_("Un documento cancelado no admite un compromiso nuevo."))
        if source._name == "repair.order":
            if source.sale_order_id or source.sale_order_line_id:
                raise UserError(_("Registre la nueva promesa desde el pedido de venta vinculado."))
            repair = source
        else:
            if not line.product_id or line.display_type:
                raise UserError(_("Seleccione una línea de venta con producto."))
            repair = self._sale_visit(source, line)
        product, lots, quantity = (
            self._repair_scope(source, repair, wizard.lot_ids)
            if repair
            else self._sale_product_scope(line, wizard.lot_ids)
        )
        if lots:
            lots.check_access("read")
        if any(
            lot.product_id != product or (lot.company_id and lot.company_id != source.company_id)
            for lot in lots
        ):
            raise UserError(_("Las series deben coincidir con el producto y empresa pactados."))
        if repair and self.sudo().search_count([("repair_id", "=", repair.id)]):
            raise UserError(_("La visita ya tiene un compromiso original. Consulte su historial."))
        self.sudo().with_context({}, **{_KEY: _CAPTURE}).create(
            {
                **terms,
                "company_id": source.company_id.id,
                "sale_line_id": line.id,
                "repair_id": repair.id,
                "product_id": product.id,
                "lot_ids": [Command.set(lots.ids)],
                "quantity": quantity,
                "actor_id": self.env.uid,
            }
        )

    def _append_change(self, commitment, kind, terms, reason):
        reason = (reason or "").strip()
        if not reason:
            raise UserError(_("Indique el motivo del cambio acordado."))
        if terms["agreed_at"] < commitment.agreed_at:
            raise UserError(_("El cambio no puede anteceder a la aceptación original."))
        changes = commitment.change_ids
        if changes.filtered(
            lambda change: change.kind == kind
            and change.reason == reason
            and all(change[name] == value for name, value in terms.items())
        ):
            return
        if any(change.kind == "cancel" for change in changes):
            raise UserError(_("El compromiso ya tiene una cancelación acordada."))
        if kind == "cancel" and changes and terms["agreed_at"] < max(changes.mapped("agreed_at")):
            raise UserError(_("La cancelación no puede ser anterior a la última reprogramación."))
        changes = self.env["mc.rov.customer.commitment.change"].sudo()
        changes.with_context({}, **{_KEY: _CAPTURE}).create(
            {
                **terms,
                "commitment_id": commitment.id,
                "kind": kind,
                "reason": reason,
                "actor_id": self.env.uid,
            }
        )

    def _capture_wizard(self, source, wizard):
        self._authorize_source(source, "write")
        # Un UPDATE neutro serializa también transacciones con una instantánea anterior.
        lock_source(source)
        self._authorize_source(source, "write")
        line = wizard.sale_line_id
        if source._name == "sale.order":
            line.check_access("read")
            if not line or line.order_id != source:
                raise AccessError(_("Seleccione una línea del pedido de origen."))
            lock_source(line, access="read")
            if line.order_id != source:
                raise AccessError(_("La línea ya no pertenece al pedido de origen."))
            domain = [("sale_line_id", "=", line.id)]
        else:
            if line:
                raise AccessError(_("El origen de la promesa es la visita de reparación."))
            domain = [("repair_id", "=", source.id), ("sale_line_id", "=", False)]

        commitment = self.sudo().search(domain, limit=1)
        if commitment and commitment.company_id != source.company_id:
            raise AccessError(_("El historial pertenece a otra empresa."))
        terms = wizard._terms()
        if wizard.operation == "formalize":
            if not commitment:
                self._create_commitment(source, line, wizard, terms)
            elif not (
                all(commitment[name] == value for name, value in terms.items())
                and (not wizard.lot_ids or wizard.lot_ids == commitment.lot_ids)
            ):
                raise UserError(_("Ya existe una promesa original. Registre un cambio acordado."))
        else:
            if not commitment:
                raise UserError(_("Formalice primero la promesa en su documento de origen."))
            self._append_change(commitment, wizard.operation, terms, wizard.reason)

    def _open_capture(self, source):
        self._authorize_source(source, "write")
        field = "sale_id" if source._name == "sale.order" else "repair_id"
        defaults = {f"default_{field}": source.id}
        if source._name == "sale.order" and source.commitment_date:
            local = fields.Datetime.context_timestamp(
                source.with_context(tz="America/Santiago"), source.commitment_date
            )
            defaults.update(
                {
                    "default_precision": "hour",
                    "default_promised_at": fields.Datetime.to_string(source.commitment_date),
                    "default_promised_date": fields.Date.to_string(local.date()),
                }
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Registrar acuerdo con el cliente"),
            "res_model": "mc.rov.customer.commitment.wizard",
            "views": [(self.env.ref("mc_rov.view_customer_commitment_wizard_form").id, "form")],
            "target": "new",
            "context": defaults,
        }

    def _open_history(self, source):
        self._authorize_source(source)
        field = "sale_id" if source._name == "sale.order" else "repair_id"
        history = self.env["mc.rov.customer.commitment.history"].create({field: source.id})
        return {
            "type": "ir.actions.act_window",
            "name": _("Compromisos al cliente"),
            "res_model": history._name,
            "res_id": history.id,
            "views": [(self.env.ref("mc_rov.view_customer_commitment_history_form").id, "form")],
            "target": "new",
        }


class CustomerCommitmentChange(models.Model):
    """Conserva cada cambio acordado sin modificar la fecha original."""

    _name = "mc.rov.customer.commitment.change"
    _description = "Cambio acordado de compromiso al cliente"
    _order = "agreed_at, id"
    _check_company_auto = True

    commitment_id = fields.Many2one(
        "mc.rov.customer.commitment",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(related="commitment_id.company_id", store=True)
    kind = fields.Selection(
        [("reprogram", "Reprogramación"), ("cancel", "Cancelación")], required=True
    )
    promised_date = fields.Date(string="Nuevo día pactado")
    promised_at = fields.Datetime(string="Nueva fecha y hora pactadas")
    agreed_at = fields.Datetime(required=True, string="Acordado el")
    reason = fields.Text(required=True, string="Motivo")
    evidence = fields.Text(required=True, string="Referencia al respaldo")
    actor_id = fields.Many2one("res.users", required=True, ondelete="restrict")

    _deadline_by_kind = models.Constraint(
        """
        CHECK ((kind = 'cancel' AND promised_date IS NULL AND promised_at IS NULL)
            OR (kind = 'reprogram' AND ((promised_date IS NOT NULL) <> (promised_at IS NOT NULL))))
        """,
        "Una reprogramación conserva exactamente un plazo. Una cancelación no tiene plazo.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        check_capture(self.env)
        return super().create(vals_list)

    def write(self, vals):
        # pylint: disable=method-required-super
        raise AccessError(_("El cambio conserva los términos acordados y su evidencia."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_history(self):
        raise AccessError(_("No se elimina el historial de cambios de compromisos."))


def can_capture(source):
    """Refleja en la vista el permiso que vuelve a comprobar la escritura."""
    return (
        isinstance(source.id, int)
        and source.env.user.has_group(SUPERVISOR_GROUP)
        and source.company_id in source.env.companies
        and source.has_access("write")
    )


class SaleOrder(models.Model):
    """Abre la captura y consulta en el pedido de venta."""

    _inherit = "sale.order"

    mc_can_capture_commitment = fields.Boolean(compute="_compute_mc_can_capture_commitment")

    @api.depends("company_id")
    @api.depends_context("uid", "company")
    def _compute_mc_can_capture_commitment(self):
        for order in self:
            order.mc_can_capture_commitment = can_capture(order)

    def action_mc_customer_commitment(self):
        return self.env["mc.rov.customer.commitment"]._open_capture(self)

    def action_mc_customer_commitments(self):
        return self.env["mc.rov.customer.commitment"]._open_history(self)


class RepairOrder(models.Model):
    """Abre la captura y consulta en la orden de reparación."""

    _inherit = "repair.order"

    mc_can_capture_commitment = fields.Boolean(compute="_compute_mc_can_capture_commitment")

    @api.depends("company_id")
    @api.depends_context("uid", "company")
    def _compute_mc_can_capture_commitment(self):
        for order in self:
            order.mc_can_capture_commitment = can_capture(order)

    def action_mc_customer_commitment(self):
        return self.env["mc.rov.customer.commitment"]._open_capture(self)

    def action_mc_customer_commitments(self):
        return self.env["mc.rov.customer.commitment"]._open_history(self)
