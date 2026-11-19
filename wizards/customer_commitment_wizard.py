"""Captura explícita y consulta autorizada del historial de compromisos F3."""

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import format_date, format_datetime


def wizard_source(wizard):
    """Resuelve un único documento incluso si se manipuló el contexto del asistente."""
    wizard.ensure_one()
    if bool(wizard.sale_id) == bool(wizard.repair_id):
        raise AccessError(_("Seleccione un único documento de origen."))
    return wizard.sale_id or wizard.repair_id


class CustomerCommitmentWizard(models.TransientModel):
    """Recoge los términos del acuerdo y conserva el alcance de origen."""

    _name = "mc.rov.customer.commitment.wizard"
    _description = "Registrar acuerdo de entrega al cliente"

    sale_id = fields.Many2one("sale.order", readonly=True, string="Pedido de venta")
    repair_id = fields.Many2one("repair.order", readonly=True, string="Orden de reparación")
    sale_line_id = fields.Many2one("sale.order.line", string="Línea de venta")
    sale_product_id = fields.Many2one("product.product", compute="_compute_sale_product")
    sale_product_type = fields.Selection(related="sale_product_id.type", compute_sudo=False)
    operation = fields.Selection(
        [
            ("formalize", "Formalizar promesa original"),
            ("reprogram", "Registrar reprogramación"),
            ("cancel", "Registrar cancelación"),
        ],
        required=True,
        default="formalize",
        string="Acción",
    )
    lot_ids = fields.Many2many(
        "stock.lot",
        string="Series pactadas",
        help="Indique las series ya pactadas si el cliente acordó series específicas.",
    )
    precision = fields.Selection(
        [("day", "Día"), ("hour", "Fecha y hora")], default="day", string="Precisión del plazo"
    )
    promised_date = fields.Date(string="Día pactado (Santiago)")
    promised_at = fields.Datetime(string="Fecha y hora pactadas")
    agreed_at = fields.Datetime(
        required=True, default=fields.Datetime.now, string="Aceptado por el cliente el"
    )
    reason = fields.Text(string="Motivo del cambio")
    evidence = fields.Text(required=True, string="Referencia al respaldo del acuerdo")

    @api.depends("sale_id", "sale_line_id")
    @api.depends_context("uid", "company")
    def _compute_sale_product(self):
        for wizard in self:
            line, order = wizard.sale_line_id, wizard.sale_id
            wizard.sale_product_id = (
                line.product_id
                if line
                and order
                and order.has_access("read")
                and line.has_access("read")
                and line.order_id == order
                and order.company_id in self.env.companies
                else False
            )

    @api.constrains("sale_id", "repair_id", "sale_line_id", "lot_ids")
    def _check_document_references(self):
        # El ORM eleva las restricciones. Los documentos se comprueban como el actor.
        wizards = self.with_user(self.env.uid)
        for wizard in wizards:
            source = wizard_source(wizard)
            wizard.env["mc.rov.customer.commitment"]._authorize_source(source, "write")
            wizard.sale_line_id.check_access("read")
            wizard.lot_ids.check_access("read")
            if wizard.sale_line_id and wizard.sale_line_id.order_id != wizard.sale_id:
                raise AccessError(_("La línea no pertenece al pedido de origen."))

    @api.onchange("sale_line_id")
    def _onchange_sale_line_id(self):
        self.lot_ids = False

    def _terms(self):
        self.ensure_one()
        evidence = (self.evidence or "").strip()
        if not evidence:
            raise UserError(_("Indique la referencia al respaldo del acuerdo."))
        if not self.agreed_at or self.agreed_at > fields.Datetime.now():
            raise UserError(_("Indique una aceptación ya ocurrida."))
        if self.operation == "cancel":
            promised_date = promised_at = False
        else:
            promised_date = self.promised_date if self.precision == "day" else False
            promised_at = self.promised_at if self.precision == "hour" else False
            if not promised_date and not promised_at:
                raise UserError(_("Indique el plazo aceptado por el cliente."))
        return {
            "evidence": evidence,
            "agreed_at": self.agreed_at,
            "promised_date": promised_date,
            "promised_at": promised_at,
        }

    def action_apply(self):
        self.ensure_one()
        self.check_access("write")
        self.env["mc.rov.customer.commitment"]._capture_wizard(wizard_source(self), self)
        return {"type": "ir.actions.act_window_close"}


class CustomerCommitmentHistory(models.TransientModel):
    """Muestra promesas y cambios tras comprobar el permiso de lectura en cada consulta."""

    _name = "mc.rov.customer.commitment.history"
    _description = "Historial de compromisos al cliente"

    sale_id = fields.Many2one("sale.order", readonly=True, string="Pedido de venta")
    repair_id = fields.Many2one("repair.order", readonly=True, string="Orden de reparación")
    content = fields.Html(compute="_compute_content", string="Historial")

    @api.constrains("sale_id", "repair_id")
    def _check_history_source(self):
        for history in self.with_user(self.env.uid):
            history.env["mc.rov.customer.commitment"]._authorize_source(wizard_source(history))

    def _history_entry(self, entry, title, reason=False):
        deadline = "-"
        if entry.promised_date:
            deadline = format_date(self.env, entry.promised_date)
        elif entry.promised_at:
            deadline = format_datetime(self.env, entry.promised_at, tz="America/Santiago")
        return Markup(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td>"
            "<td>{}</td><td>{}</td><td>{}</td></tr>"
        ).format(
            title,
            deadline,
            format_datetime(self.env, entry.agreed_at, tz="America/Santiago"),
            format_datetime(self.env, entry.create_date, tz="America/Santiago"),
            entry.actor_id.name,
            entry.evidence,
            reason or "-",
        )

    def _history_table(self, row, source):
        sale = row.repair_id.sale_order_id.with_env(self.env)
        related_sale = (
            sale.display_name
            if sale
            and not row.sale_line_id
            and sale != source
            and sale.has_access("read")
            and sale.company_id in self.env.companies
            else False
        )
        scope = row.sale_line_id.name if row.sale_line_id else row.repair_id.display_name
        product = row.product_id.with_env(self.env)
        lots = row.lot_ids.with_env(self.env)
        series = ", ".join(lots.mapped("name")) if lots and lots.has_access("read") else False
        rows = [self._history_entry(row, _("Promesa original"))]
        for change in row.change_ids:
            title = _("Cancelación") if change.kind == "cancel" else _("Reprogramación")
            rows.append(self._history_entry(change, title, change.reason))
        return Markup(
            "<h5>{}</h5><p>{} · {} {}</p>{}{}"
            '<div class="table-responsive"><table class="table table-sm mb-4">'
            "<thead><tr><th>{}</th><th>{}</th><th>{}</th><th>{}</th><th>{}</th>"
            "<th>{}</th><th>{}</th></tr></thead><tbody>{}</tbody></table></div>"
        ).format(
            scope,
            product.display_name if product.has_access("read") else _("Producto restringido"),
            row.quantity,
            _("unidades"),
            (
                Markup("<p>{}</p>").format(_("Pedido vinculado posteriormente: %s", related_sale))
                if related_sale
                else ""
            ),
            Markup("<p>{}</p>").format(_("Series pactadas: %s", series)) if series else "",
            _("Acuerdo"),
            _("Plazo (Santiago)"),
            _("Aceptado (Santiago)"),
            _("Registrado (Santiago)"),
            _("Autor"),
            _("Respaldo"),
            _("Motivo"),
            Markup().join(rows),
        )

    @api.depends("sale_id", "repair_id")
    @api.depends_context("uid", "company", "lang")
    def _compute_content(self):
        ledger = self.env["mc.rov.customer.commitment"]
        for history in self:
            source = wizard_source(history)
            rows = ledger._rows_for_source(source)
            history.content = Markup().join(
                history._history_table(row, source) for row in rows
            ) or Markup("<p>{}</p>").format(_("Sin compromiso definido."))
