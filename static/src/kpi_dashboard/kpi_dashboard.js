/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { user, userBus } from "@web/core/user";
import { useSetupAction } from "@web/search/action_hook";
import { deserializeDateTime, formatDateTime } from "@web/core/l10n/dates";
import { DashboardLoader } from "./loader";
import { firstPassPresentation, formatPercent } from "./presentation";

const SERVICE = "mc.rov.kpi.dashboard";
const SECTIONS = [
    { key: "summary", label: "Resumen" }, { key: "quality", label: "Calidad" },
    { key: "tracking", label: "Seguimiento" }, { key: "coverage", label: "Cobertura y definiciones" },
    { key: "production", label: "Producción" }, { key: "findings", label: "Hallazgos" },
];
const PROCESSES = {
    all: "Todos los procesos", repair: "Reparación", manufacturing: "Fabricación",
    acceptance: "Aceptación", quality: "Calidad", engineering: "Ingeniería", inventory: "Inventario",
};
const COVERAGE = {
    available: "Disponible", partial: "Parcial", restricted: "Sin acceso",
    capture_pending: "Captura pendiente", source_pending: "Fuente por verificar",
};

export class KPIDashboard extends Component {
    static template = "mc_rov.KPIDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.sections = SECTIONS;
        this.processOptions = Object.entries(PROCESSES).map(([key, label]) => ({ key, label }));
        const saved = this.props.state?.dashboard || {};
        this.state = useState({
            section: SECTIONS.some((item) => item.key === saved.section) ? saved.section : "summary",
            dateFrom: typeof saved.dateFrom === "string" ? saved.dateFrom : "",
            dateTo: typeof saved.dateTo === "string" ? saved.dateTo : "",
            process: Object.hasOwn(PROCESSES, saved.process) ? saved.process : "all",
            modelId: Number.isInteger(saved.modelId) && saved.modelId > 0 ? saved.modelId : false,
            revision: typeof saved.revision === "string" ? saved.revision : "latest",
            dimension: saved.dimension === "component" ? "component" : "finding",
            unit: ["visits", "equipment"].includes(saved.unit) ? saved.unit : "observations",
            customerId: Number.isInteger(saved.customerId) && saved.customerId > 0 ? saved.customerId : false,
            severity: ["informativo", "atencion", "impide_operar"].includes(saved.severity) ? saved.severity : "all",
            intervention: ["repair", "maintenance"].includes(saved.intervention) ? saved.intervention : "all",
            report: null, error: "", loading: true, opening: false, detailError: "",
        });
        this.destroyed = false;
        this.loader = new DashboardLoader(this.state, () => this.fetchData(), () => this.companyKey);
        useSetupAction({ getLocalState: () => ({ dashboard: this.exportState() }) });
        useBus(userBus, "ACTIVE_COMPANIES_CHANGED", () => {
            this.state.modelId = false;
            this.state.customerId = false;
            this.state.revision = "latest";
            return this.refresh();
        });
        onWillStart(() => this.loader.load());
        onMounted(() => {
            // Una empresa cambiada durante el primer RPC puede descartar su respuesta.
            if (!this.state.report && !this.state.error && !this.state.loading) return this.loader.load();
        });
        onWillUnmount(() => { this.destroyed = true; this.loader.destroy(); });
    }

    get companyKey() { return user.activeCompanies.map((company) => company.id).join(","); }
    get companyLabel() { return user.activeCompanies.map((company) => company.name).join(", "); }
    get generatedLabel() {
        const value = this.state.report?.generated_at;
        return value ? formatDateTime(deserializeDateTime(value), { tz: "America/Santiago" }) : "Sin fecha";
    }

    exportState() {
        const { section, dateFrom, dateTo, process, modelId, revision, dimension, unit, customerId, severity, intervention } = this.state;
        return { section, dateFrom, dateTo, process, modelId, revision, dimension, unit, customerId, severity, intervention };
    }

    fetchData() {
        const kwargs = {
            date_from: this.state.dateFrom || false, date_to: this.state.dateTo || false,
            process: this.state.process, context: { ...user.context },
        };
        if (this.productionMode) kwargs.production_filters = {
            model_id: this.state.modelId, revision: this.state.revision,
            dimension: this.state.dimension, unit: this.state.unit,
            customer_id: this.state.customerId, severity: this.state.severity, intervention: this.state.intervention,
        };
        return this.orm.call(SERVICE, "get_dashboard", [], kwargs);
    }

    refresh() { this.state.detailError = ""; return this.loader.load(); }
    selectSection(key) {
        if (!SECTIONS.some((item) => item.key === key)) return;
        this.state.section = key;
        if (this.productionMode) return this.refresh();
    }
    setFilter(key, value) {
        if (!["dateFrom", "dateTo", "process", "modelId", "revision", "dimension", "unit", "customerId", "severity", "intervention"].includes(key)) return;
        this.state[key] = ["modelId", "customerId"].includes(key) ? (Number(value) || false) : value;
        if (key === "modelId") { this.state.revision = "latest"; this.state.customerId = false; }
        return this.refresh();
    }

    get productionMode() { return ["production", "findings"].includes(this.state.section); }
    get productionMetrics() {
        const row = this.state.report?.production;
        return row?.available === true ? row.metrics : null;
    }
    get modelOptions() { return this.productionMetrics?.filters?.model_options || []; }
    get revisionOptions() { return this.productionMetrics?.filters?.revision_options || []; }
    get customerOptions() { return this.productionMetrics?.filters?.customer_options || []; }
    get volumeCards() {
        const metrics = this.productionMetrics;
        if (!metrics) return [];
        return [
            { key: "repair", source: "repair_done", title: "Reparaciones terminadas", count: metrics.repair.visits,
                note: `${metrics.repair.equipment} equipos distintos · primer cierre por visita` },
            ...[["manufactured", "Unidades fabricadas"], ["accepted", "Unidades aceptadas"],
                ["released", "Unidades liberadas"], ["outbound", "Unidades salidas al cliente"]]
                .map(([key, title]) => ({ key, source: key, title, count: metrics.manufacturing[key], note: "Unidades por hito acreditado en el período" })),
        ];
    }
    get paretoRows() {
        return (this.productionMetrics?.findings?.rows || []).map((row) => ({
            ...row, percentLabel: formatPercent(row.percent), cumulativeLabel: formatPercent(row.cumulative_percent),
            barStyle: `width:${Math.max(0, Math.min(100, row.percent))}%`,
        }));
    }
    get paretoTotalLabel() {
        const report = this.productionMetrics?.findings;
        const unit = { observations: "observaciones", visits: "pertenencias de visitas a categorías", equipment: "pertenencias de equipos a categorías" };
        return report ? `${report.total} ${unit[report.unit] || "registros"}` : "Sin datos autorizados";
    }

    get portfolioCards() {
        return [
            ["repair", "Órdenes de reparación abiertas"],
            ["manufacturing", "Órdenes de fabricación abiertas"],
        ].map(([key, title]) => {
            const row = this.state.report?.portfolio?.[key];
            const valid = row?.available === true && Number.isInteger(row.count) && row.count >= 0;
            return { key, title, available: valid,
                headline: valid ? String(row.count) : row?.available === false ? "Sin acceso" : "Sin dato",
                detailKey: valid ? row.detail_key : null };
        });
    }

    get qualityCards() {
        return [["repair", "Reparaciones", "Órdenes de reparación consultadas"],
            ["manufacturing", "Equipos nuevos", "Unidades realmente fabricadas"]]
            .map(([key, title, unit]) => {
                const row = this.state.report?.quality?.[key];
                return { key, title, unit, ...firstPassPresentation(row),
                    evaluated: row?.available ? row.metrics?.evaluated : null,
                    detailKey: row?.available ? row.detail_key : null };
            });
    }

    get trackingRows() {
        const rows = this.state.report?.tracking?.processes;
        return Array.isArray(rows) ? rows.map((row) => ({ ...row, label: PROCESSES[row.key] || "Proceso" })) : [];
    }
    get coverageRows() {
        const rows = this.state.report?.coverage;
        return Array.isArray(rows) ? rows.map((row) => ({ ...row, label: COVERAGE[row.status] || "Sin dato" })) : [];
    }
    compliance(metric) {
        if (!metric) return "Sin dato";
        return metric.known ? `${formatPercent(metric.value)} (${metric.on_time}/${metric.known})` : "Sin base";
    }
    hours(value) {
        return typeof value === "number" && Number.isFinite(value)
            ? `${new Intl.NumberFormat("es-CL", { maximumFractionDigits: 1 }).format(value)} h` : "Sin dato";
    }

    openProductionSources(key) {
        return this.openDetail(key, "action_production_sources", {
            date_from: this.state.dateFrom || false, date_to: this.state.dateTo || false,
            model_id: this.state.modelId, revision: this.state.revision,
            dimension: this.state.dimension, unit: this.state.unit,
            customer_id: this.state.customerId, severity: this.state.severity,
            intervention: this.state.intervention,
        });
    }

    async openDetail(key, method = "action_detail", filters = {}) {
        if (this.state.opening) return;
        const company = this.companyKey;
        this.state.opening = true;
        this.state.detailError = "";
        try {
            const action = await this.orm.call(SERVICE, method, [key], { ...filters, context: { ...user.context } });
            if (this.destroyed) return;
            if (company !== this.companyKey) { await this.loader.load(); return; }
            await this.action.doAction(action);
        } catch {
            if (!this.destroyed) this.state.detailError = "No fue posible abrir el detalle autorizado.";
        } finally {
            if (!this.destroyed) this.state.opening = false;
        }
    }
}

registry.category("actions").add("mc_rov.kpi_dashboard", KPIDashboard);
