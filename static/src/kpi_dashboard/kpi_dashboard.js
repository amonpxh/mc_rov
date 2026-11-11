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
            report: null, error: "", loading: true, opening: false, detailError: "",
        });
        this.destroyed = false;
        this.loader = new DashboardLoader(this.state, () => this.fetchData(), () => this.companyKey);
        useSetupAction({ getLocalState: () => ({ dashboard: this.exportState() }) });
        useBus(userBus, "ACTIVE_COMPANIES_CHANGED", () => this.loader.load());
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
        const { section, dateFrom, dateTo, process } = this.state;
        return { section, dateFrom, dateTo, process };
    }

    fetchData() {
        return this.orm.call(SERVICE, "get_dashboard", [], {
            date_from: this.state.dateFrom || false, date_to: this.state.dateTo || false,
            process: this.state.process, context: { ...user.context },
        });
    }

    refresh() { this.state.detailError = ""; return this.loader.load(); }
    selectSection(key) {
        if (SECTIONS.some((item) => item.key === key)) this.state.section = key;
    }
    setFilter(key, value) {
        if (!["dateFrom", "dateTo", "process"].includes(key)) return;
        this.state[key] = value;
        return this.refresh();
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

    async openDetail(key) {
        if (this.state.opening) return;
        const company = this.companyKey;
        this.state.opening = true;
        this.state.detailError = "";
        try {
            const action = await this.orm.call(SERVICE, "action_detail", [key], { context: { ...user.context } });
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
