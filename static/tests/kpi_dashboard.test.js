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
