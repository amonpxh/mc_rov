"""Consulta F3 de promesas y salidas acreditadas por documentos autorizados."""

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.tools import float_compare

from .customer_commitment_metrics import summarize_commitments
from .production_kpi_metrics import local_day, period_bounds


class CustomerCommitmentKPI(models.AbstractModel):
    """Concilia cada promesa contra sus propios movimientos sin exponer la evidencia privada."""

    _name = "mc.rov.customer.commitment.kpi"
    _description = "Cumplimiento de compromisos al cliente"

    def _visible(self, model, ids):
        if not ids:
            return set()
        try:
            return set(
                self.env[model].with_context(active_test=False).search([("id", "in", ids)]).ids
            )
        except AccessError:
            return set()

    def _history(self, companies):
        rows = (
            self.env["mc.rov.customer.commitment"].sudo().search([("company_id", "in", companies)])
        )
        sales = self._visible("sale.order", rows.sale_line_id.order_id.ids)
        lines = self._visible("sale.order.line", rows.sale_line_id.ids)
        repairs = self._visible("repair.order", rows.repair_id.ids)
        lots = self._visible("stock.lot", rows.lot_ids.ids)
        products = self._visible("product.product", rows.product_id.ids)
        return rows.filtered(
            lambda row: (
                not row.sale_line_id
                or (row.sale_line_id.id in lines and row.sale_line_id.order_id.id in sales)
            )
            and (not row.repair_id or row.repair_id.id in repairs)
            and row.product_id.id in products
            and set(row.lot_ids.ids) <= lots
        )

    def _base_moves(self, row, cutoff):
        """Una visita se concilia por su relación operativa, incluso en una venta de servicio."""
        if row.repair_id:
            links = Domain("repair_id", "=", row.repair_id.id)
            # El picking_id nativo de Reparación corresponde a la recepción.
            ledger = self.env["mc.rov.customer.dispatch"].sudo()
            repair_pickings = ledger.search(
                [
                    ("repair_ids", "in", row.repair_id.ids),
                    ("company_id", "=", row.company_id.id),
                    ("create_date", "<=", cutoff),
                ]
            ).picking_id
            current = self._dispatches(repair_pickings, cutoff, row.company_id.id)
            explicit = [
                pid for pid, evidence in current.items() if row.repair_id in evidence.repair_ids
            ]
            if explicit:
                links |= Domain("picking_id", "in", explicit)
        else:
            links = Domain("sale_line_id", "=", row.sale_line_id.id)
        return (
            self.env["stock.move"]
            .sudo()
            .search(
                links
                & Domain("company_id", "=", row.company_id.id)
                & Domain("product_id", "=", row.product_id.id)
                & Domain("state", "=", "done")
                & Domain("location_id.usage", "=", "internal")
                & Domain("location_dest_id.usage", "=", "customer")
                & Domain("date", ">=", row.agreed_at)
            )
        )

    def _related_moves(self, row, outbound):
        """Seguir devoluciones y reentregas por la cadena nativa de origen."""
        moves = self.env["stock.move"].sudo()
        seen, frontier = outbound, outbound
        while frontier:
            frontier = (
                moves.search(
                    [
                        ("company_id", "=", row.company_id.id),
                        ("product_id", "=", row.product_id.id),
                        ("state", "=", "done"),
                        ("origin_returned_move_id", "in", frontier.ids),
                    ]
                )
                - seen
            )
            seen |= frontier
        return seen

    def _dispatches(self, pickings, cutoff, company):
        events = (
            self.env["mc.rov.customer.dispatch"]
            .sudo()
            .search(
                [
                    ("picking_id", "in", pickings.ids),
                    ("company_id", "=", company),
                    ("create_date", "<=", cutoff),
                ],
                order="id desc",
            )
        )
        current = {}
        for event in events:
            current.setdefault(event.picking_id.id, event)
        return current

    def _authorized_lines(self, row, outbound):
        moves = self._related_moves(row, outbound).with_env(self.env)
        moves.check_access("read")
        moves.picking_id.check_access("read")
        lines = moves.move_line_ids
        lines.check_access("read")
        lines.lot_id.check_access("read")
        if len(row.lot_ids) == row.quantity:
            return lines.filtered(lambda line: not line.lot_id or line.lot_id in row.lot_ids)
        return lines

    def _departure_times(self, line, row, evidence):
        """Una salida sin constancia conserva su incertidumbre y nunca usa date_done."""
        if evidence:
            repairs = evidence.repair_ids.filtered(
                lambda repair: repair.lot_id.id == line.lot_id.id
            )
            if repairs and repairs != row.repair_id:
                # La misma serie acreditada para una visita no acredita otra promesa.
                return None
            if evidence.kind != "invalidated" and evidence._evidence_matches(line.picking_id):
                return (
                    evidence.effective_date or None,
                    evidence.effective_at or None,
                    max(evidence.create_date, line.move_id.date),
                )
        return None, None, line.move_id.date

    def _movement_value(self, line, row, customer, dispatches):
        route = line.location_id.usage, line.location_dest_id.usage
        if route not in (("internal", "customer"), ("customer", "internal")):
            return False
        move = line.move_id
        partner = (line.picking_id.partner_id or move.partner_id).commercial_partner_id
        quantity = line.product_uom_id._compute_quantity(
            line.quantity, line.product_id.uom_id, round=False
        )
        if (
            not partner
            or partner != customer
            or not line.lot_id
            or float_compare(quantity, 1, precision_rounding=line.product_id.uom_id.rounding)
        ):
            return None
        kind = "return" if route == ("customer", "internal") else "outbound"
        times = (
            (None, move.date, move.date)
            if kind == "return"
            else self._departure_times(line, row, dispatches.get(line.picking_id.id))
        )
        if times is None:
            return None
        effective_date, effective_at, recorded_at = times
        return {
            "id": line.id,
            "lot_id": line.lot_id.id,
            "kind": kind,
            "effective_date": effective_date,
            "effective_at": effective_at,
            "recorded_at": recorded_at,
        }

    def _movement_rows(self, row, cutoff):
        outbound = self._base_moves(row, cutoff)
        lines = self._authorized_lines(row, outbound)
        dispatches = self._dispatches(lines.picking_id, cutoff, row.company_id.id)
        customer = row._commitment_source().with_env(self.env).partner_id.commercial_partner_id
        result, parents = [], defaultdict(list)
        unknown = (
            not outbound and bool(row.repair_id) and self._has_unlinked_outbound(row, customer)
        )
        for line in lines:
            value = self._movement_value(line, row, customer, dispatches)
            if value is None:
                unknown = True
            elif value:
                result.append((value, line.move_id.origin_returned_move_id.id))
                if value["kind"] == "return":
                    parents[(line.move_id.id, value["lot_id"])].append(line.id)
        normalized = []
        for value, parent in result:
            matched = parents.get((parent, value["lot_id"]), ())
            if len(matched) == 1 and value["kind"] == "outbound":
                value["after_id"] = matched[0]
            normalized.append(value)
        return normalized, unknown

    def _has_unlinked_outbound(self, row, customer):
        """Una coincidencia visible solo sirve para advertir cobertura insuficiente."""
        if not row.lot_ids or not customer:
            return False
        return bool(
            self.env["stock.move.line"].search_count(
                [
                    ("company_id", "=", row.company_id.id),
                    ("lot_id", "in", row.lot_ids.ids),
                    ("move_id.state", "=", "done"),
                    ("move_id.date", ">=", row.agreed_at),
                    ("location_id.usage", "=", "internal"),
                    ("location_dest_id.usage", "=", "customer"),
                    ("picking_id.partner_id.commercial_partner_id", "=", customer.id),
                ],
                limit=1,
            )
        )

    def _commitment_input(self, row, cutoff):
        movements, unknown = self._movement_rows(row, cutoff)
        return {
            "id": row.id,
            "quantity": row.quantity,
            "lot_ids": row.lot_ids.ids,
            "promised_date": row.promised_date or None,
            "promised_at": row.promised_at or None,
            "agreed_at": row.agreed_at,
            "recorded_at": row.create_date,
            "changes": [
                {
                    "kind": change.kind,
                    "promised_date": change.promised_date or None,
                    "promised_at": change.promised_at or None,
                    "agreed_at": change.agreed_at,
                    "recorded_at": change.create_date,
                }
                for change in row.change_ids
            ],
            "movements": movements,
            "coverage_unknown": unknown,
        }

    def _coverage(self, companies, captured):
        """Cuenta trabajos elegibles con los mismos orígenes que la formalización."""
        coverage = dict.fromkeys(
            (
                "sale_lines_without_promise",
                "repair_visits_without_promise",
                "repair_visits_with_unresolved_sale_link",
            )
        )
        root = self.env["stock.lot"]._get_rov_root_category()
        if not root:
            return dict.fromkeys(coverage, 0)
        domain = [("company_id", "in", companies), ("product_id.categ_id", "child_of", root.id)]
        service_lines = []
        captured_lines = set(captured.sale_line_id.ids)
        try:
            repairs = self.env["repair.order"].search([*domain, ("state", "!=", "cancel")])
            service_lines = repairs.filtered(
                lambda repair: repair.lot_id
                and repair.sale_order_id
                and repair.sale_order_line_id.order_id == repair.sale_order_id
            ).sale_order_line_id.ids
            captured_repairs = repairs & captured.repair_id.with_env(self.env)
            captured_lines.update(captured_repairs.sale_order_line_id.ids)
            uncovered = repairs - captured_repairs
            coverage["repair_visits_without_promise"] = len(
                uncovered.filtered(lambda repair: not repair.sale_order_id and repair.lot_id)
            )
            coverage["repair_visits_with_unresolved_sale_link"] = len(
                uncovered.filtered(
                    lambda repair: repair.sale_order_id and not repair.sale_order_line_id
                )
            )
        except AccessError:
            # No deducir visitas o líneas de servicio que el lector no puede consultar.
            pass
        try:
            self.env["sale.order"].check_access("read")
            coverage["sale_lines_without_promise"] = self.env["sale.order.line"].search_count(
                Domain("company_id", "in", companies)
                & Domain("state", "=", "sale")
                & Domain("id", "not in", sorted(captured_lines))
                & (
                    Domain("product_id.categ_id", "child_of", root.id)
                    | Domain("id", "in", service_lines)
                )
            )
        except AccessError:
            pass
        return coverage

    def _add_detail(self, metrics, rows, start, end):
        by_id = {row.id: row for row in rows}
        selected = [
            row
            for row in metrics["rows"]
            if row["in_due"]
            or row["in_completed"]
            or (row["cancelled_at"] and start <= local_day(row["cancelled_at"]) <= end)
        ]
        for item in selected[:50]:
            row = by_id[item["id"]]
            item["origin"] = row._commitment_source().with_env(self.env).display_name
            item["cancel_reason"] = next(
                (
                    change.reason
                    for change in row.change_ids
                    if change.kind == "cancel"
                    and item["cancelled_at"] == change.agreed_at.isoformat()
                ),
                None,
            )
        metrics["rows"] = selected[:50]
        metrics["detail_total"] = len(selected)

    @api.model
    def get_summary(self, date_from=False, date_to=False):
        companies = self.env["mc.rov.kpi.dashboard"]._check_caller()
        cutoff = fields.Datetime.now()
        try:
            start, end = period_bounds(date_from, date_to)
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("Seleccione un período válido.")) from exc
        if not any(self.env[model].has_access("read") for model in ("sale.order", "repair.order")):
            raise AccessError(_("Se requiere acceso a los documentos del compromiso."))
        rows = self._history(companies)
        inputs = [self._commitment_input(row, cutoff) for row in rows]
        dates = [row["promised_date"] or local_day(row["promised_at"]) for row in inputs]
        today = local_day(cutoff)
        earliest = min([today, *(day for day in dates if day)])
        start = start or (min(earliest, end) if end else earliest)
        end = end or max(today, start)
        metrics = summarize_commitments(inputs, date_from=start, date_to=end, as_of=cutoff)
        metrics["coverage"] = self._coverage(companies, rows)
        self._add_detail(metrics, rows, start, end)
        return metrics
