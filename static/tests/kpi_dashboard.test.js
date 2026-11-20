import { describe, expect, test } from "@odoo/hoot";
import { click, select } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, mockService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { registry } from "@web/core/registry";
import { userBus } from "@web/core/user";

const SERVICE = "mc.rov.kpi.dashboard";
const TAG = "mc_rov.kpi_dashboard";
const metrics = (overrides = {}) => ({ population: 4, passed: 2, failed: 1, pending: 1, unknown: 0,
    evaluated: 3, value: 200 / 3, coverage_percent: 75, ...overrides });
const report = () => ({
    generated_at: "2026-11-11 18:00:00",
    portfolio: {
        repair: { available: true, count: 4, detail_key: "portfolio_repair" },
        manufacturing: { available: true, count: 1, detail_key: "portfolio_manufacturing" },
    },
    quality: {
        repair: { available: true, metrics: metrics(), detail_key: "quality_repair" },
        manufacturing: { available: true, metrics: metrics({ population: 0, passed: 0, failed: 0, pending: 0, evaluated: 0, value: null, coverage_percent: null }), detail_key: "quality_manufacturing" },
    },
    tracking: { available: true, processes: [{ key: "repair", available: false, metrics: null }] },
    production: { available: true, metrics: {
        repair: { visits: 3, equipment: 2, unknown_revision: 1 },
        manufacturing: { manufactured: 2, accepted: 1, released: 1, outbound: 0, reversed: 0, unknown_revision: 0 },
        findings: { total: 3, unit: "observations", unclassified: 0, missing_unit: 0, rows: [
            { key: 1, label: "Corrosión", count: 2, percent: 200 / 3, cumulative_percent: 200 / 3 },
            { key: 2, label: "Fuga", count: 1, percent: 100 / 3, cumulative_percent: 100 },
        ] },
        coverage: { unknown_repair_closure: 1, unknown_detection: 2, unknown_observation_capture: 3, ambiguous_configurations: 0 },
        filters: { revision: "latest", revision_options: [{ key: "bom:1:v2", label: "Diseño 2" }],
            model_options: [{ id: 1, label: "ROV QA" }], customer_options: [{ id: 7, label: "Cliente QA" }], resolved_revisions: ["bom:1:v2"] },
        balances: { manufactured_not_accepted: 1, accepted_not_released: 0, released_in_workshop: 1, outbound: 0, unbuilt: 0, missing_prerequisite: 0 },
    } },
    coverage: ["F1", "F2", "F3", "F4", "F5", "F6", "Q1", "Q2", "Q3", "Q4", "A1"].map((key) => ({ key, title: key, status: "capture_pending", unit: "Unidad QA", requirement: "Dato pendiente QA", decision: "Decisión QA", source: "Fuente QA", population: "Población QA", formula: "Fórmula QA" })),
});

async function setup(options = {}) {
    expect(registry.category("actions").contains(TAG)).toBe(true, { message: "Falta la acción de indicadores ROV" });
    const Dashboard = registry.category("actions").get(TAG);
    const calls = [], actions = [];
    let fails = false;
    mockService("orm", { call(model, method, args, kwargs) {
        expect(model).toBe(SERVICE);
        calls.push({ method, args, kwargs });
        if (fails) return Promise.reject(new Error("Detalle privado del servidor"));
        return Promise.resolve(method === "get_dashboard" ? (options.report || report()) : { type: "ir.actions.act_window", res_model: "repair.order", views: [[false, "list"]] });
    } });
    mockService("action", { doAction: (action) => actions.push(action) });
    const dashboard = await mountWithCleanup(Dashboard, { props: { action: { tag: TAG }, state: options.state || {} } });
    await animationFrame();
    return { dashboard, calls, actions, fail: () => { fails = true; } };
}

describe("mc_rov KPI dashboard", () => {
    defineModels(mailModels);

    test("Detenciones muestra cartera actual y duración por separado", async () => {
        const data = report();
        data.detentions = { available: true, metrics: {
            registered_stopped_orders: 1, open_orders: 4, registered_stopped_percent: 25,
            recorded_seconds: 7200, recorded_interval_count: 2, orders_without_recorded_intervals: 3,
            unknown_duration_intervals: 0, by_cause: {
                materials: { label: "Repuestos/materiales", recorded_seconds: 7200, recorded_interval_count: 1 },
                client: { label: "Cliente", recorded_seconds: 3600, recorded_interval_count: 1 },
            },
        } };
        const { calls } = await setup({ report: data });
        await click("[data-section='detentions']");
        await animationFrame();
        expect("[data-kpi-detentions]").toHaveText(/1 de 4/);
        expect("[data-kpi-detentions]").toHaveText(/Repuestos\/materiales/);
        expect("[data-kpi-detentions]").toHaveText(/3 órdenes sin historial registrado/);
        await click("[data-kpi-detention-process]");
        await select("manufacturing");
        await animationFrame();
        expect(calls.at(-1).kwargs.detention_filters).toEqual({ process: "manufacturing" });
    });

    test("Detenciones sin acceso no muestra indicadores numéricos", async () => {
        const data = report();
        data.detentions = { available: false, metrics: null };
        await setup({ report: data });
        await click("[data-section='detentions']");
        await animationFrame();
        expect("[data-kpi-detentions]").toHaveText(/Indicador no disponible/);
        expect("[data-kpi-detentions] .mc_kpi_value").toHaveCount(0);
    });

    test("Compromisos presenta los dos denominadores y conserva el estado sin evidencia", async () => {
        const data = report();
        data.commitments = { available: true, metrics: {
            due: { denominator: 10, on_time: 8, late: 1, overdue: 1, unknown: 2, cancelled: 0, percentage: 80 },
            completed: { denominator: 9, on_time: 8, late: 1, overdue: 0, unknown: 0, cancelled: 0, percentage: 800 / 9 },
            coverage: { sale_lines_without_promise: 1, repair_visits_without_promise: 2 },
            rows: [],
        } };
        const { calls } = await setup({ report: data });
        await click("[data-section='commitments']");
        await animationFrame();
        expect("[data-kpi-commitments]").toHaveText(/8 de 10/);
        expect("[data-kpi-commitments]").toHaveText(/8 de 9/);
        expect("[data-kpi-commitments]").toHaveText(/2 sin evidencia suficiente/);
        expect(calls.at(-1).kwargs.customer_commitments).toBe(true);
    });

    test("Compromisos restringidos no presenta ceros", async () => {
        const data = report();
        data.commitments = { available: false, metrics: null };
        await setup({ report: data });
        await click("[data-section='commitments']");
        await animationFrame();
        expect("[data-kpi-commitments]").toHaveText(/Indicador no disponible/);
        expect("[data-kpi-commitments] .mc_kpi_value").toHaveCount(0);
    });

    test("Plazo de reparación muestra cobertura y conserva una mediana de cero días", async () => {
        const data = report();
        data.repair_lead_time = { available: true, metrics: {
            samples: 2, departed: 4, missing_arrival: 1, invalid_chronology: 0,
            ambiguous_departure: 1, median_days: 0, p80_days: null,
            distribution: [{ minimum: 0, maximum: 2, count: 2 }],
        } };
        const { calls } = await setup({ report: data });
        await click("[data-section='repair_lead_time']");
        await animationFrame();
        expect("[data-kpi-repair-lead-time]").toHaveText(/2 de 4 visitas/);
        expect("[data-kpi-repair-lead-time]").toHaveText(/1 sin llegada acreditada/);
        expect("[data-kpi-repair-lead-time] .mc_kpi_card:first-child .mc_kpi_value").toHaveText("0");
        expect(calls.at(-1).kwargs.repair_lead_time).toBe(true);
    });


    test("Retornos muestra dictámenes sin inferir una tasa", async () => {
        const data = report();
        data.repair_returns = { available: true, metrics: {
            observed_returns: 3, observed_related_returns: 1, observed_pending_returns: 1,
            observed_unrelated_returns: 1, confirmed_originals_within_window: 1, outside_window: 0,
        } };
        const { calls } = await setup({ report: data });
        await click("[data-section='repair_returns']");
        await animationFrame();
        expect("[data-kpi-repair-returns] .mc_kpi_value").toHaveCount(4);
        expect("[data-kpi-repair-returns]").toHaveText(/Tasa pendiente de seguimiento acreditado/);
        expect(calls.at(-1).kwargs.repair_returns).toBe(true);
    });

    test("Producción distingue visitas equipos y hitos", async () => {
        await setup();
        await click("[data-section='production']");
        await animationFrame();
        expect("[data-volume='repair']").toHaveText(/3/);
        expect("[data-volume='repair']").toHaveText(/2 equipos/);
        expect("[data-volume='manufactured']").toHaveText(/2/);
        expect("[data-volume='outbound']").toHaveText(/0/);
    });

    test("Hallazgos muestra Pareto de observaciones y acumulado", async () => {
        await setup();
        await click("[data-section='findings']");
        await animationFrame();
        expect(".mc_kpi_pareto").toHaveText(/Corrosión/);
        expect(".mc_kpi_pareto").toHaveText(/Acumulado/);
        expect(".mc_kpi_pareto").toHaveText(/100/);
        expect(".mc_kpi_pareto_total").toHaveText(/3 observaciones/);
    });

    test("Última vigente es inicial y Todas viaja al servidor", async () => {
        const { calls } = await setup();
        await click("[data-section='production']");
        await animationFrame();
        expect("[data-kpi-revision]").toHaveValue("latest");
        await click("[data-kpi-revision]");
        await select("all");
        await animationFrame();
        expect(calls.at(-1).kwargs.production_filters.revision).toBe("all");
    });

    test("Modelo seleccionado viaja como identificador", async () => {
        const { calls } = await setup();
        await click("[data-section='production']");
        await animationFrame();
        await click("[data-kpi-model]");
        await select("1");
        await animationFrame();
        expect(calls.at(-1).kwargs.production_filters.model_id).toBe(1);
    });

    test("Ausencia de acceso no muestra ceros de producción", async () => {
        const data = report();
        data.production = { available: false, metrics: null };
        await setup({ report: data });
        await click("[data-section='production']");
        await animationFrame();
        expect(".mc_kpi_volume_restricted").toHaveText(/Sin acceso/);
        expect("[data-volume]").toHaveCount(0);
    });

    test("Cobertura de detección no se convierte en hallazgo de hoy", async () => {
        await setup();
        await click("[data-section='findings']");
        await animationFrame();
        expect(".mc_kpi_findings_coverage").toHaveText(/Sin fecha de detección acreditada: 2/);
        expect(".mc_kpi_findings_coverage").toHaveText(/Sin captura histórica: 3/);
    });

    test("Cliente e intervención filtran con contexto histórico", async () => {
        const { calls } = await setup();
        await click("[data-section='production']");
        await animationFrame();
        await click("[data-kpi-customer]"); await select("7"); await animationFrame();
        expect(calls.at(-1).kwargs.production_filters.customer_id).toBe(7);
        await click("[data-kpi-intervention]"); await select("repair"); await animationFrame();
        expect(calls.at(-1).kwargs.production_filters.intervention).toBe("repair");
    });

    test("Saldos se separan de hitos del período", async () => {
        await setup();
        await click("[data-section='production']");
        await animationFrame();
        expect(".mc_kpi_balances").toHaveText(/Saldos al corte/);
        expect(".mc_kpi_balances").toHaveText(/Fabricadas sin aceptar: 1/);
        expect(".mc_kpi_balances").toHaveText(/Liberadas en taller: 1/);
    });

    test("Tarjeta abre documentos de origen con los mismos filtros", async () => {
        const { calls, actions } = await setup();
        await click("[data-section='production']"); await animationFrame();
        await click("[data-volume-source='repair_done']"); await animationFrame();
        expect(calls.at(-1).method).toBe("action_production_sources");
        expect(calls.at(-1).args).toEqual(["repair_done"]);
        expect(calls.at(-1).kwargs.revision).toBe("latest");
        expect(actions.length).toBe(1);
    });

    test("Cambio de empresa limpia cortes de modelo cliente y revisión", async () => {
        const { calls } = await setup({ state: { dashboard: {
            section: "production", modelId: 1, customerId: 7, revision: "bom:1:v2",
        } } });
        userBus.trigger("ACTIVE_COMPANIES_CHANGED"); await animationFrame();
        expect(calls.at(-1).kwargs.production_filters.model_id).toBe(false);
        expect(calls.at(-1).kwargs.production_filters.customer_id).toBe(false);
        expect(calls.at(-1).kwargs.production_filters.revision).toBe("latest");
    });

    test("Resumen distingue órdenes de unidades producidas", async () => {
        await setup();
        expect(".mc_kpi_portfolio[data-source='repair']").toHaveText(/Órdenes de reparación abiertas/);
        expect(".mc_kpi_quality[data-source='manufacturing']").toHaveText(/Unidades realmente fabricadas/);
    });

    test("muestra porcentaje y numerador denominador", async () => {
        await setup();
        expect(".mc_kpi_quality[data-source='repair']").toHaveText(/66,7 %/);
        expect(".mc_kpi_quality[data-source='repair']").toHaveText(/2\/3/);
    });

    test("selección vacía muestra Sin base", async () => {
        await setup();
        expect(".mc_kpi_quality[data-source='manufacturing'] .mc_kpi_value").toHaveText("Sin base");
    });

    test("sin acceso no muestra conteos", async () => {
        const value = report();
        value.quality.repair = { available: false, metrics: null };
        await setup({ report: value });
        expect(".mc_kpi_quality[data-source='repair'] .mc_kpi_value").toHaveText("Sin acceso");
        expect(".mc_kpi_quality[data-source='repair'] .mc_kpi_counts").toHaveCount(0);
    });

    test("Cobertura conserva las once fichas pendientes", async () => {
        await setup();
        await click("[data-section='coverage']");
        await animationFrame();
        expect(".mc_kpi_catalog [data-family]").toHaveCount(11);
        expect("[data-family='F3']").toHaveText(/Captura pendiente/);
        expect("[data-family='F3']").toHaveText(/Fuente QA/);
        expect("[data-family='F3']").toHaveText(/Fórmula QA/);
    });

    test("el selector de proceso afecta solo al RPC de seguimiento", async () => {
        const { calls } = await setup();
        await click("[data-section='tracking']");
        await animationFrame();
        await click("[data-kpi-process]");
        await select("repair");
        await animationFrame();
        expect(calls.at(-1).kwargs.process).toBe("repair");
        expect(".mc_kpi_filters").toHaveText(/Los pendientes y vencimientos siguen siendo actuales/);
    });

    test("abrir detalle usa la acción autorizada del servidor", async () => {
        const { calls, actions } = await setup();
        await click(".mc_kpi_portfolio[data-source='repair'] button");
        await animationFrame();
        expect(calls.at(-1).method).toBe("action_detail");
        expect(calls.at(-1).args).toEqual(["portfolio_repair"]);
        expect(actions[0].res_model).toBe("repair.order");
    });

    test("error de consulta borra cifras y muestra mensaje seguro", async () => {
        const { fail } = await setup();
        fail();
        await click("[data-kpi-refresh]");
        await animationFrame();
        expect("[role='alert']").toHaveText(/No fue posible cargar los indicadores/);
        expect(".mc_kpi_portfolio").toHaveCount(0);
        expect(".mc_kpi_content").not.toHaveText(/Detalle privado del servidor/);
    });

    test("volver conserva pestaña pero consulta nuevas cifras", async () => {
        const { dashboard, calls } = await setup({ state: { dashboard: { section: "quality", report: { stale: true } } } });
        expect(dashboard.state.section).toBe("quality");
        expect(calls.length).toBe(1);
        expect(".mc_kpi_portfolio").toHaveCount(0);
        expect(".mc_kpi_quality").toHaveCount(2);
    });

    test("evento de empresa vuelve a consultar", async () => {
        const { calls } = await setup();
        userBus.trigger("ACTIVE_COMPANIES_CHANGED");
        await animationFrame();
        expect(calls.length).toBe(2);
    });

    test("alta aprobación no oculta baja cobertura", async () => {
        const value = report();
        value.quality.repair.metrics = metrics({ population: 100, passed: 1, failed: 0, pending: 0, unknown: 99, evaluated: 1, value: 100, coverage_percent: 1 });
        await setup({ report: value });
        expect(".mc_kpi_quality[data-source='repair'] .mc_kpi_value").toHaveText("100 %");
        expect(".mc_kpi_quality[data-source='repair'] .mc_kpi_coverage").toHaveText(/1\/100/);
        expect(".mc_kpi_quality[data-source='repair'] .mc_kpi_coverage").toHaveText(/1 %/);
    });
});
