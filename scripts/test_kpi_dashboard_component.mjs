import assert from "node:assert/strict";
import { readFile, access } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { resolve, dirname, extname } from "node:path";
import { SourceTextModule, SyntheticModule } from "node:vm";
import test from "node:test";

const sourceRoot = fileURLToPath(new URL("../static/src/kpi_dashboard/", import.meta.url));
const report = () => ({
    generated_at: "2026-11-11 18:00:00",
    portfolio: { repair: { available: true, count: 4, detail_key: "portfolio_repair" } },
    quality: { repair: { available: true, metrics: { population: 4, passed: 2, failed: 1, pending: 1, unknown: 0, evaluated: 3, value: 200 / 3 } } },
    tracking: { available: true, processes: [] }, coverage: [],
});

async function setup(saved = {}) {
    const filename = resolve(sourceRoot, "kpi_dashboard.js");
    try { await access(filename); } catch { assert.fail("Falta el componente del tablero"); }
    const starts = [], mounted = [], unmounts = [], calls = [], actions = [], listeners = new Map();
    const user = { activeCompanies: [{ id: 1, name: "QA" }], context: { allowed_company_ids: [1] } };
    const bus = {};
    const stateSaver = {};
    const orm = { async call(model, method, args, kwargs) {
        calls.push({ model, method, args, kwargs });
        return method === "get_dashboard" ? report() : { type: "ir.actions.act_window", res_model: "repair.order" };
    } };
    const services = { orm, action: { async doAction(value) { actions.push(value); } } };
    const registry = { category() { return { add() {} }; } };
    const mocks = new Map([
        ["@odoo/owl", { Component: class {}, useState: (value) => value, onWillStart: (fn) => starts.push(fn), onMounted: (fn) => mounted.push(fn), onWillUnmount: (fn) => unmounts.push(fn) }],
        ["@web/core/registry", { registry }],
        ["@web/core/utils/hooks", { useService: (name) => services[name], useBus: (_bus, event, fn) => listeners.set(event, fn) }],
        ["@web/core/user", { user, userBus: bus }],
        ["@web/search/action_hook", { useSetupAction: (value) => Object.assign(stateSaver, value) }],
        ["@web/core/l10n/dates", { deserializeDateTime: (value) => value, formatDateTime: (value) => value }],
    ]);
    const modules = new Map();
    async function moduleFor(id) {
        if (modules.has(id)) return modules.get(id);
        let module;
        if (mocks.has(id)) {
            const values = mocks.get(id);
            module = new SyntheticModule(Object.keys(values), function () {
                for (const [name, value] of Object.entries(values)) this.setExport(name, value);
            }, { identifier: id });
        } else {
            module = new SourceTextModule(await readFile(id, "utf8"), { identifier: id });
        }
        modules.set(id, module);
        await module.link((specifier, parent) => {
            if (!specifier.startsWith(".")) return moduleFor(specifier);
            let filename = resolve(dirname(parent.identifier), specifier);
            if (!extname(filename)) filename += ".js";
            return moduleFor(filename);
        });
        return module;
    }
    const module = await moduleFor(filename);
    await module.evaluate();
    const dashboard = new module.namespace.KPIDashboard();
    dashboard.props = { state: saved };
    dashboard.setup();
    for (const fn of starts) await fn();
    for (const fn of mounted) await fn();
    return { dashboard, user, calls, actions, orm, stateSaver, listeners, unmounts };
}

test("consulta únicamente la API del tablero con empresas activas", async () => {
    const { calls } = await setup();
    assert.equal(calls[0].model, "mc.rov.kpi.dashboard");
    assert.equal(calls[0].method, "get_dashboard");
    assert.deepEqual(calls[0].args, []);
    assert.deepEqual(calls[0].kwargs.context.allowed_company_ids, [1]);
});

test("volver restaura sección y filtros pero vuelve a consultar cifras", async () => {
    const { dashboard, calls, stateSaver } = await setup({ dashboard: { section: "tracking", dateFrom: "2026-11-01", dateTo: "2026-11-10", process: "repair", report: { obsolete: true } } });
    assert.equal(dashboard.state.section, "tracking");
    assert.equal(calls[0].kwargs.date_from, "2026-11-01");
    assert.equal(dashboard.state.report.obsolete, undefined);
    assert.equal(stateSaver.getLocalState().dashboard.section, "tracking");
    assert.equal(stateSaver.getLocalState().dashboard.report, undefined);
});

test("cambiar una pestaña no altera la población ni repite la consulta", async () => {
    const { dashboard, calls } = await setup();
    dashboard.selectSection("quality");
    assert.equal(dashboard.state.section, "quality");
    assert.equal(calls.length, 1);
});

test("detalle usa la acción que devuelve el servidor", async () => {
    const { dashboard, calls, actions } = await setup();
    await dashboard.openDetail("quality_repair");
    assert.equal(calls.at(-1).method, "action_detail");
    assert.deepEqual(calls.at(-1).args, ["quality_repair"]);
    assert.equal(actions[0].res_model, "repair.order");
});

test("cambio de empresa vuelve a consultar sin conservar cifras", async () => {
    const { user, listeners, calls } = await setup();
    user.activeCompanies = [{ id: 2, name: "QA dos" }];
    user.context = { allowed_company_ids: [2] };
    await listeners.get("ACTIVE_COMPANIES_CHANGED")();
    assert.deepEqual(calls.at(-1).kwargs.context.allowed_company_ids, [2]);
});

test("pestaña guardada desconocida vuelve a Resumen", async () => {
    const { dashboard } = await setup({ dashboard: { section: "foreign" } });
    assert.equal(dashboard.state.section, "summary");
});

test("respuesta de detalle de una empresa anterior no navega", async () => {
    const { dashboard, orm, user, actions, calls } = await setup();
    const original = orm.call;
    let finish;
    orm.call = (model, method, args, kwargs) => method === "action_detail"
        ? new Promise((resolve) => { finish = resolve; }) : original(model, method, args, kwargs);
    const pending = dashboard.openDetail("quality_repair");
    user.activeCompanies = [{ id: 2, name: "Otra QA" }];
    user.context = { allowed_company_ids: [2] };
    finish({ type: "ir.actions.act_window", res_model: "repair.order" });
    await pending;
    assert.equal(actions.length, 0);
    assert.deepEqual(calls.at(-1).kwargs.context.allowed_company_ids, [2]);
});

test("desmontar durante el detalle impide navegar después", async () => {
    const { dashboard, orm, unmounts, actions } = await setup();
    let finish;
    orm.call = () => new Promise((resolve) => { finish = resolve; });
    const pending = dashboard.openDetail("quality_repair");
    for (const fn of unmounts) fn();
    finish({ type: "ir.actions.act_window", res_model: "repair.order" });
    await pending;
    assert.equal(actions.length, 0);
});
