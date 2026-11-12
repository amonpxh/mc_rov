"""Consulta de volumen e historial con autorización de todos los documentos de origen."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain

from .production_kpi_metrics import local_day, pareto, period_bounds, summarize_events


class ProductionKPIService(models.AbstractModel):
    """No usa las páginas del Centro ni interpreta ausencia de evidencia como cierre."""

    _name = "mc.rov.production.kpi"
    _description = "Volumen de producción y Pareto ROV"

    def _sources(self, model_id):
        companies = self.env["mc.rov.kpi.dashboard"]._check_caller()
        if model_id is not False and (
            isinstance(model_id, bool) or not isinstance(model_id, int) or model_id < 1
        ):
            raise ValidationError(_("Seleccione un modelo válido."))
        root = self.env["stock.lot"]._get_rov_root_category()
        product_domain = [("categ_id", "child_of", root.id)] if root else [("id", "=", 0)]
        if model_id:
            template = self.env["product.template"].browse(model_id)
            if not template.exists():
                raise AccessError(_("El modelo no está disponible."))
            template.check_access("read")
            template.product_variant_ids.check_access("read")
            product_domain.append(("product_tmpl_id", "=", model_id))
        products = (
            self.env["product.product"].with_context(active_test=False).search(product_domain)
        )
        common = [("company_id", "in", companies), ("product_id", "in", products.ids)]
        repairs = self.env["repair.order"].with_context(active_test=False).search(common)
        productions = self.env["mrp.production"].with_context(active_test=False).search(common)
        # La relación de revisión no tiene company_id; la empresa del hecho se filtra
        # en el ledger y la serie/reparación deben ser legibles sin sudo.
        revisions = self.env["mc.rov.revision"].search([("product_id", "in", products.ids)])
        for source in (repairs, productions, revisions):
            source.check_access("read")
            source.product_id.check_access("read")
            if "lot_id" in source._fields:
                source.lot_id.check_access("read")
        return companies, products, repairs, productions, revisions

    def _events(self, sources):
        companies, _products, repairs, productions, revisions = sources
        domain = Domain.AND(
            [
                [("company_id", "in", companies)],
                Domain.OR(
                    [
                        [("repair_id", "in", repairs.ids), ("kind", "=", "repair_done")],
                        [("production_id", "in", productions.ids), ("kind", "!=", "observation")],
                        [("revision_id", "in", revisions.ids), ("kind", "=", "observation")],
                    ]
                ),
            ]
        )
        events = self.env["mc.rov.production.event"].sudo().search(domain)
        # Nunca omitir una serie o producto histórico ilegible después de elevar.
        self.env["stock.lot"].browse(events.lot_id.ids).check_access("read")
        self.env["product.product"].browse(events.product_id.ids).check_access("read")
        return events

    def _revision_options(self, products, events, selector):
        if not isinstance(selector, str):
            raise ValidationError(_("Seleccione Todas, Última o una revisión acreditada."))
        options = {}
        for event in events:
            key = event.payload.get("revision_key")
            if key:
                options[key] = {"key": key, "label": event.payload.get("revision_label") or key}
        boms = self.env["mrp.bom"].search(
            [
                ("product_tmpl_id", "in", products.product_tmpl_id.ids),
                ("company_id", "in", [False, *self.env.companies.ids]),
                ("active", "=", True),
            ]
        )
        configurations = {}
        for bom in boms:
            configuration = bom.product_tmpl_id.id, bom.product_id.id, bom.code or ""
            configurations.setdefault(configuration, []).append(bom)
        latest = []
        ambiguous = 0
        for candidates in configurations.values():
            if len(candidates) != 1:
                ambiguous += 1
                continue
            bom = candidates[0]
            key = f"bom:{bom.id}:v{bom.version}"
            options[key] = {"key": key, "label": f"{bom.code or 'BoM'} · revisión {bom.version}"}
            latest.append(key)
        if selector not in ("all", "latest") and selector not in options:
            raise ValidationError(
                _("La revisión seleccionada no está acreditada en estas fuentes.")
            )
        resolved = "all" if selector == "all" else latest if selector == "latest" else [selector]
        return resolved, list(options.values()), ambiguous

    def _normalized(self, events):
        return [
            {
                **event.payload,
                "identity": event.identity,
                "kind": event.kind,
                "at": fields.Datetime.to_string(event.at) if event.at else False,
                "lot_id": event.lot_id.id,
            }
            for event in events
        ]

    @api.model
    def get_summary(
        self,
        date_from=False,
        date_to=False,
        model_id=False,
        revision="latest",
        dimension="finding",
        unit="observations",
    ):
        # API de filtros explícitos; mantener nombres estables para RPC y pruebas.
        # pylint: disable=too-many-arguments,too-many-locals
        try:
            bounds = period_bounds(date_from, date_to)
        except (ValueError, TypeError) as error:
            raise ValidationError(_("El período no es válido.")) from error
        sources = self._sources(model_id)
        events = self._events(sources)
        resolved, options, ambiguous = self._revision_options(sources[1], events, revision)
        normalized = self._normalized(events)
        report = summarize_events(normalized, date_from, date_to, resolved)
        observations = self._observations(normalized, bounds, resolved)
        try:
            report["findings"] = pareto(observations, dimension=dimension, unit=unit)
        except ValueError as error:
            raise ValidationError(_("La unidad de Pareto no es válida.")) from error
        repairs = sources[2]
        report["coverage"] = {
            "unknown_repair_closure": len(
                repairs.filtered(lambda row: row.state == "done")
                - events.filtered(lambda row: row.kind == "repair_done").repair_id
            ),
            "unknown_detection": len(
                events.filtered(lambda row: row.kind == "observation" and not row.at)
            ),
            "ambiguous_configurations": ambiguous,
        }
        report["filters"] = {
            "revision": revision,
            "revision_options": options,
            "resolved_revisions": resolved,
            "model_id": model_id,
        }
        return report

    def _observations(self, events, bounds, resolved):
        result = []
        for event in events:
            if event["kind"] != "observation":
                continue
            day = local_day(event.get("at"))
            if day is None or (bounds[0] and day < bounds[0]) or (bounds[1] and day > bounds[1]):
                continue
            if resolved != "all" and event.get("revision_key") not in resolved:
                continue
            result.append(event)
        return result
