"""Tablero de gestión: consulta completa sin alterar decisiones ni historiales."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain

from .kpi_dashboard_catalog import DEFINITIONS, INITIAL_FAMILIES


SOURCES = {
    "repair": ("repair", "orders", "mc.rov.repair.acceptance.kpi"),
    "manufacturing": ("manufacturing", "manufacturing", "mc.rov.new.acceptance.kpi"),
}
SUMMARY_FIELDS = (
    "basis",
    "population",
    "passed",
    "failed",
    "pending",
    "unknown",
    "evaluated",
    "value",
    "coverage_percent",
)
DETAILS = {
    "portfolio_repair": ("repair", "open"),
    "portfolio_manufacturing": ("manufacturing", "open"),
    "quality_repair": ("repair", "all"),
    "quality_manufacturing": ("manufacturing", "all"),
}


class KPIDashboard(models.AbstractModel):
    """Presenta las métricas existentes solo sobre fuentes legibles y empresas activas."""

    _name = "mc.rov.kpi.dashboard"
    _description = "Tablero de gestión ROV"

    def _check_caller(self):
        user = self.env.user
        if (
            user.share
            or user._is_public()
            or not user.has_group("base.group_user")
            or not user.has_group("mc_rov.group_work_assignment_team")
        ):
            raise AccessError(_("Se requiere permiso de consulta del trabajo del equipo."))
        # Evaluar companies valida también un contexto RPC falsificado.
        return self.env.companies.ids

    def _source_domain(self, key, state_filter):
        topic, kind, _service = SOURCES[key]
        center = self.env["mc.rov.work.center"]
        if state_filter == "all":
            center = center.with_context(active_test=False)
        definition, domain = center._get_domain(topic, kind, state_filter)
        if state_filter == "all":
            # Los adaptadores históricos exigen una empresa activa concreta.
            domain = list(Domain.AND([domain, [("company_id", "in", self.env.companies.ids)]]))
        return definition[0], domain

    def _portfolio(self, key):
        try:
            model, domain = self._source_domain(key, "open")
            return {
                "available": True,
                "count": self.env[model].search_count(domain),
                "detail_key": "portfolio_" + key,
            }
        except AccessError:
            return {"available": False, "count": None, "detail_key": False}

    def _quality(self, key):
        try:
            model, domain = self._source_domain(key, "all")
            # La consulta no usa la lista paginada de Centro ni filtra órdenes cerradas.
            sources = self.env[model].with_context(active_test=False).search(domain)
            summary = self.env[SOURCES[key][2]].get_summary(sources.ids)
            return {
                "available": True,
                "metrics": {name: summary[name] for name in SUMMARY_FIELDS},
                "detail_key": "quality_" + key,
            }
        except AccessError:
            # Un historial necesario ilegible impide la tasa completa; no se omite su fallo.
            return {"available": False, "metrics": None, "detail_key": False}

    def _coverage(self, portfolio, quality):
        rows = []
        for key, title, status, unit, requirement in INITIAL_FAMILIES:
            if key == "Q1":
                available = sum(row["available"] for row in quality.values())
                status = (
                    "available"
                    if available == len(SOURCES)
                    else "partial" if available else "restricted"
                )
            if key == "F1" and not any(row["available"] for row in portfolio.values()):
                status = "restricted"
            rows.append(
                {
                    "key": key,
                    "title": title,
                    "status": status,
                    "unit": unit,
                    "requirement": requirement,
                    **DEFINITIONS[key],
                }
            )
        return rows

    @api.model
    # Conserva parámetros públicos previos y añade un filtro opcional independiente.
    # pylint: disable=too-many-arguments
    def get_dashboard(
        self,
        date_from=False,
        date_to=False,
        process="all",
        production_filters=None,
        detention_filters=None,
        customer_commitments=False,
    ):
        companies = self._check_caller()
        # El servicio conserva sus validaciones de fechas/proceso y sus propias zonas.
        try:
            tracking = self.env["mc.rov.work.kpi"].get_summary(
                date_from=date_from, date_to=date_to, process=process
            )
            tracking["available"] = True
        except AccessError:
            tracking = {"available": False, "processes": [], "partial": True}
        portfolio = {key: self._portfolio(key) for key in SOURCES}
        quality = {key: self._quality(key) for key in SOURCES}
        report = {
            "generated_at": fields.Datetime.to_string(fields.Datetime.now()),
            "cohort": {
                "basis": "current_authorized_rov_orders",
                "company_ids": companies,
                "includes_closed": True,
                "includes_archived": True,
                "period_applies_to": "tracking_closures_only",
            },
            "portfolio": portfolio,
            "quality": quality,
            "tracking": tracking,
            "coverage": self._coverage(portfolio, quality),
        }
        if production_filters is not None:
            if not isinstance(production_filters, dict) or set(production_filters) - {
                "model_id",
                "revision",
                "dimension",
                "unit",
                "customer_id",
                "severity",
                "intervention",
            }:
                raise ValidationError(_("Los filtros de producción no son válidos."))
            try:
                report["production"] = {
                    "available": True,
                    "metrics": self.env["mc.rov.production.kpi"].get_summary(
                        date_from=date_from, date_to=date_to, **production_filters
                    ),
                }
            except AccessError:
                report["production"] = {"available": False, "metrics": None}
        if detention_filters is not None:
            if not isinstance(detention_filters, dict) or set(detention_filters) - {"process"}:
                raise ValidationError(_("Los filtros de detenciones no son válidos."))
            try:
                metrics = self.env["mc.rov.detention.kpi"].get_summary(
                    date_from=date_from, date_to=date_to, **detention_filters
                )
                report["detentions"] = {"available": True, "metrics": metrics}
            except AccessError:
                report["detentions"] = {"available": False, "metrics": None}
        if not isinstance(customer_commitments, bool):
            raise ValidationError(_("La opción de compromisos no es válida."))
        if customer_commitments:
            try:
                metrics = self.env["mc.rov.customer.commitment.kpi"].get_summary(
                    date_from=date_from, date_to=date_to
                )
                report["commitments"] = {"available": True, "metrics": metrics}
            except AccessError:
                report["commitments"] = {"available": False, "metrics": None}
        return report

    @api.model
    def action_detail(self, key):
        self._check_caller()
        if not isinstance(key, str) or key not in DETAILS:
            raise ValidationError(_("El destino del indicador no es válido."))
        source, state_filter = DETAILS[key]
        _model, domain = self._source_domain(source, state_filter)
        topic, kind, _service = SOURCES[source]
        action = self.env["mc.rov.work.center"].action_list(topic, kind, state_filter=state_filter)
        action["domain"] = domain
        if state_filter == "all":
            action["context"] = {**action.get("context", {}), "active_test": False}
        return action
