import { Component, onWillUnmount, useSubEnv, xml } from "@odoo/owl";
import { describe, expect, test } from "@odoo/hoot";
import { click, select } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, mockService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { useSetupAction } from "@web/search/action_hook";
import { registry } from "@web/core/registry";

const ASSIGNMENT = "mc.rov.work.assignment";

// The host is tested with a view substitute; real native View behavior has its
// own integration checks. This substitute never duplicates native controllers.
class ViewProbe extends Component {
    static props = ["*"];
    static template = xml`<div data-native-view="" t-att-data-native-model="props.action.res_model">
        <span t-esc="props.viewType"/>
    </div>`;
}

function requireIntegration() {
    const Center = registry.category("actions").get("mc_rov.work_center");
    const present = Boolean(Center.components?.AssignedWorkView);
    expect(present).toBe(true, { message: "Falta la integración de vistas dentro del Centro" });
    if (!present) return null;
    class CenterProbe extends Center {}
    CenterProbe.components = { ...Center.components, AssignedWorkView: ViewProbe };
    return CenterProbe;
}

const options = [
    { key: "all", label: "Todos los procesos", available: true, hint: "" },
    { key: "repair", label: "Reparación", available: true, hint: "" },
    { key: "manufacturing", label: "Fabricación", available: true, hint: "" },
    { key: "acceptance", label: "Aceptación", available: false, hint: "Sin actividades específicas" },
    { key: "equipment", label: "Equipo", available: true, hint: "" },
    { key: "none", label: "Sin proceso vinculado", available: true, hint: "" },
];

function mockWork({ failFirst = false, acceptanceAvailable = false } = {}) {
    const calls = [];
    const navigation = [];
    let failed = false;
    mockService("action", { doAction: (action) => navigation.push(action) });
    mockService("orm", {
        searchRead: () => Promise.resolve([{ id: 7, display_name: "Pedro" }, { id: 8, display_name: "Ana" }]),
        call(model, method, args, kwargs) {
            calls.push({ model, method, args, kwargs });
            if (model !== ASSIGNMENT) {
                return Promise.resolve(method === "get_overview" ? [
                    { topic: "repair", kind: "orders", available: true, count: 1, can_create: true },
                    { topic: "acceptance", kind: "equipment", available: true, count: 1, can_create: true },
                ] : { rows: [{ id: 1, reference: "DEMO-001", context: "Modelo", state: "Operativo" }], total: 1, next_offset: false });
            }
            if (method === "get_capabilities") return Promise.resolve({ can_view_team: true, can_coordinate: true });
            if (method === "get_processes") return Promise.resolve(options.map(option => {
                if (option.key !== "acceptance") return option;
                const available = acceptanceAvailable && kwargs.kind === "activities";
                return { ...option, available, hint: available ? "" : option.hint };
            }));
            if (failFirst && !failed) {
                failed = true;
                return Promise.reject(new Error("QA sin acceso"));
            }
            const resModel = { action_activities: "mail.activity", action_tasks: "project.task", action_projects: "project.project" }[method];
            return Promise.resolve({ type: "ir.actions.act_window", res_model: resModel,
                views: [[false, "list"], [false, "kanban"], ...(resModel === "project.project" ? [] : [[false, "calendar"]])],
                search_view_id: [false, "QA búsqueda"], domain: [], context: { allowed_company_ids: [1] } });
        },
    });
    return { calls, navigation };
}

async function choose(selector, value) {
    await click(selector);
    await select(value);
    await animationFrame();
}

describe("mc_rov embedded work", () => {
    defineModels(mailModels);

    test("entrada muestra el trabajo nativo dentro sin navegar a otra pantalla", async () => {
        const Center = requireIntegration();
        if (!Center) return;
        const { navigation } = mockWork();
        await mountWithCleanup(Center, { props: { action: { tag: "mc_rov.work_center" } } });
        expect('[data-native-model="mail.activity"]').toHaveCount(1);
        expect('.mc_work_center_table').toHaveCount(0);
        expect(navigation).toHaveLength(0);
        expect('button[aria-label="Actualizar registros"]').toBeEnabled();
    });

    test("seleccionar proceso sustituye el tablero por sus registros", async () => {
        const Center = requireIntegration();
        if (!Center) return;
        mockWork();
        await mountWithCleanup(Center, { props: { action: { tag: "mc_rov.work_center" } } });
        await click('[data-topic="acceptance"]');
        await animationFrame();
        expect('[data-native-view]').toHaveCount(0);
        expect('.mc_work_center_table').toHaveCount(1);
        await click('[data-work-assigned]');
        await animationFrame();
        expect('[data-native-view]').toHaveCount(1);
        expect('.mc_work_center_table').toHaveCount(0);
    });

    test("filtro cruza proceso empleado y alcance sin sustituir permisos", async () => {
        const Center = requireIntegration();
        if (!Center) return;
        const { calls } = mockWork();
        await mountWithCleanup(Center, { props: { action: { tag: "mc_rov.work_center" } } });
        await choose('.mc_assignment_scope', "team");
        await choose('.mc_assignment_employee', "7");
        await choose('.mc_assignment_process', "repair");
        const actionCall = calls.filter(x => x.method === "action_activities").at(-1);
        expect(actionCall.kwargs).toEqual({ scope: "team", employee_id: 7, process: "repair" });
    });

    test("tareas y proyectos usan su propio modelo y no reciben filtro de empleado", async () => {
        const Center = requireIntegration();
        if (!Center) return;
        const { calls } = mockWork();
        await mountWithCleanup(Center, { props: { action: { tag: "mc_rov.work_center" } } });
        await click('[data-assignment-kind="tasks"]');
        await animationFrame();
        expect('[data-native-model="project.task"]').toHaveCount(1);
        expect('.mc_assignment_employee').toHaveCount(0);
        expect(calls.filter(x => x.method === "action_tasks").at(-1).kwargs).toEqual({ scope: "mine", process: "all" });
        await click('[data-assignment-kind="projects"]');
        await animationFrame();
        expect('[data-native-model="project.project"]').toHaveCount(1);
        expect('[data-assignment-view="calendar"]').toHaveCount(0);
    });

    test("volver del proceso conserva alcance empleado proceso y vista", async () => {
        const Center = requireIntegration();
        if (!Center) return;
        mockWork();
        await mountWithCleanup(Center, { props: { action: { tag: "mc_rov.work_center" } } });
        await choose('.mc_assignment_scope', "team");
        await choose('.mc_assignment_employee', "7");
        await choose('.mc_assignment_process', "repair");
        await click('[data-assignment-view="list"]');
        await click('[data-topic="acceptance"]');
        await click('[data-work-assigned]');
        await animationFrame();
        expect('.mc_assignment_scope').toHaveValue("team");
        expect('.mc_assignment_employee').toHaveValue("7");
        expect('.mc_assignment_process').toHaveValue("repair");
        expect('[data-native-view]').toHaveText("list");
    });

    test("actualizar conserva busqueda nativa y descarta datos cacheados", async () => {
        const Center = requireIntegration();
        if (!Center) return;
        class RefreshProbe extends Component {
            static props = ["*"];
            static template = xml`<div data-refresh-probe="" t-att-data-cache="props.saved.state?.modelState ? 'yes' : 'no'">
                <span t-esc="props.saved.globalState?.searchModel || 'Sin búsqueda'"/>
            </div>`;
            setup() {
                this.props.register(this);
                onWillUnmount(() => this.props.register(null, this));
            }
            canLeave() { return true; }
            snapshot() { return { globalState: { searchModel: "QA NAS" }, state: { modelState: { offset: 40 } } }; }
        }
        class RefreshCenter extends Center {}
        RefreshCenter.components = { ...Center.components, AssignedWorkView: RefreshProbe };
        mockWork();
        await mountWithCleanup(RefreshCenter, { props: { action: { tag: "mc_rov.work_center" } } });
        await click('button[aria-label="Actualizar registros"]');
        await animationFrame();
        expect('[data-refresh-probe]').toHaveText("QA NAS");
        expect('[data-refresh-probe]').toHaveAttribute("data-cache", "no");
    });

    test("fallo de acceso no deja una vista anterior y permite reintentar", async () => {
        const Center = requireIntegration();
        if (!Center) return;
        mockWork({ failFirst: true });
        await mountWithCleanup(Center, { props: { action: { tag: "mc_rov.work_center" } } });
        expect('[data-native-view]').toHaveCount(0);
        expect('[data-assignment-retry]').toHaveCount(1);
        await click('[data-assignment-retry]');
        await animationFrame();
        expect('[data-native-model="mail.activity"]').toHaveCount(1);
    });

    test("aceptacion conserva busqueda empleado y alcance al actualizar", async () => {
        const Center = requireIntegration();
        if (!Center) return;
        class AcceptanceRefreshProbe extends Component {
            static props = ["*"];
            static template = xml`<div data-acceptance-refresh="">
                <span t-esc="props.saved.globalState?.searchModel || 'Sin búsqueda'"/>
            </div>`;
            setup() {
                this.props.register(this);
                onWillUnmount(() => this.props.register(null, this));
            }
            canLeave() { return true; }
            snapshot() { return { globalState: { searchModel: "QA aceptación" }, state: { modelState: { offset: 40 } } }; }
        }
        class AcceptanceCenter extends Center {}
        AcceptanceCenter.components = { ...Center.components, AssignedWorkView: AcceptanceRefreshProbe };
        const { calls } = mockWork({ acceptanceAvailable: true });
        await mountWithCleanup(AcceptanceCenter, { props: { action: { tag: "mc_rov.work_center" } } });
        await choose('.mc_assignment_scope', "team");
        await choose('.mc_assignment_employee', "7");
        await choose('.mc_assignment_process', "acceptance");
        await click('button[aria-label="Actualizar registros"]');
        await animationFrame();
        expect('.mc_assignment_scope').toHaveValue("team");
        expect('.mc_assignment_employee').toHaveValue("7");
        expect('.mc_assignment_process').toHaveValue("acceptance");
        expect('[data-acceptance-refresh]').toHaveCount(1);
        expect('[data-acceptance-refresh]').toHaveText("QA aceptación");
        expect('.mc_work_center_table').toHaveCount(0);
        expect(calls.filter(x => x.method === "action_activities").at(-1).kwargs)
            .toEqual({ scope: "team", employee_id: 7, process: "acceptance" });
    });

    test("volver de registros conserva aceptacion y una sola zona de contenido", async () => {
        const Center = requireIntegration();
        if (!Center) return;
        mockWork({ acceptanceAvailable: true });
        await mountWithCleanup(Center, { props: { action: { tag: "mc_rov.work_center" } } });
        await choose('.mc_assignment_scope', "team");
        await choose('.mc_assignment_employee', "7");
        await choose('.mc_assignment_process', "acceptance");
        await click('[data-assignment-view="list"]');
        await click('[data-topic="acceptance"]');
        await animationFrame();
        expect('[data-native-view]').toHaveCount(0);
        expect('.mc_work_center_table').toHaveCount(1);
        await click('[data-work-assigned]');
        await animationFrame();
        expect('.mc_assignment_process').toHaveValue("acceptance");
        expect('.mc_assignment_scope').toHaveValue("team");
        expect('.mc_assignment_employee').toHaveValue("7");
        expect('[data-native-view]').toHaveCount(1);
        expect('[data-native-view]').toHaveText("list");
        expect('.mc_work_center_table').toHaveCount(0);
    });

    test("aceptacion no inventa vinculos para tareas o proyectos", async () => {
        const Center = requireIntegration();
        if (!Center) return;
        const { calls } = mockWork({ acceptanceAvailable: true });
        await mountWithCleanup(Center, { props: { action: { tag: "mc_rov.work_center" } } });
        await choose('.mc_assignment_process', "acceptance");
        for (const kind of ["tasks", "projects"]) {
            await click(`[data-assignment-kind="${kind}"]`);
            await animationFrame();
            expect('.mc_assignment_process').toHaveValue("all");
            expect('.mc_assignment_process option[value="acceptance"]').toHaveCount(1);
            expect('.mc_assignment_process option[value="acceptance"]').not.toBeEnabled();
            expect(calls.filter(x => x.method === `action_${kind}`).at(-1).kwargs)
                .toEqual({ scope: "mine", process: "all" });
        }
    });
});

// These checks exercise the bridge and callback ownership. The real native
// renderers still require the STAGING browser checks (search/menu/return).
class NativeControllerProbe extends Component {
    static props = ["*"];
    static template = xml`<div>
        <button data-native-open="" t-on-click="() => props.selectRecord(17)">Abrir origen</button>
        <button data-native-create="" t-on-click="props.createRecord">Crear</button>
    </div>`;
    setup() {
        useSubEnv(Object.fromEntries(Object.entries(this.props).filter(([key]) => key.startsWith("__"))));
        useSetupAction({ getGlobalState: () => ({ searchModel: "QA búsqueda" }),
            getLocalState: () => ({ modelState: { offset: 40 } }), beforeLeave: () => false });
        expect(this.env.config.actionId).toBe(124);
        expect(this.props.loadActionMenus).toBe(true);
        expect(this.props.searchViewId).toBe(361);
        expect(this.env.config.viewSwitcherEntries).toEqual([]);
    }
}

describe("mc_rov embedded bridge", () => {
    defineModels(mailModels);
    async function mountBridge(model = "mail.activity") {
        const Native = registry.category("actions").get("mc_rov.work_center").components.AssignedWorkView;
        class BridgeProbe extends Native {}
        BridgeProbe.components = { ...Native.components, View: NativeControllerProbe };
        let bridge;
        const calls = [];
        mockService("orm", { call: (model, method, args) => {
            calls.push({ model, method, args });
            return Promise.resolve({ res_model: "repair.order", res_id: 32, views: [[false, "form"]] });
        } });
        mockService("action", { doAction: (action) => { calls.push({ action }); } });
        await mountWithCleanup(BridgeProbe, { props: {
            action: { id: 124, res_model: model, views: [[364, "list"]], search_view_id: [361, "Búsqueda"],
                context: { allowed_company_ids: [1] }, domain: [["user_id", "=", 2]] },
            viewType: "list", saved: {}, register: (value) => { bridge = value; }, onError: () => {},
        } });
        return { bridge, calls };
    }
    test("estado y bloqueo de salida pertenecen a la vista nativa", async () => {
        const { bridge } = await mountBridge();
        expect(bridge.snapshot()).toEqual({ globalState: { searchModel: "QA búsqueda" }, state: { modelState: { offset: 40 } } });
        expect(await bridge.canLeave()).toBe(false);
    });
    test("actividad abre su origen mediante la consulta protegida", async () => {
        const { calls } = await mountBridge();
        await click('[data-native-open]');
        expect(calls[0]).toEqual({ model: ASSIGNMENT, method: "action_open_source", args: [17] });
        expect(calls[1].action.res_id).toBe(32);
    });
    test("tarea abre y crea su formulario con el contexto de la accion", async () => {
        const { calls } = await mountBridge("project.task");
        await click('[data-native-open]');
        await click('[data-native-create]');
        expect(calls.map(x => [x.action.res_model, x.action.res_id]))
            .toEqual([["project.task", 17], ["project.task", false]]);
        expect(calls[1].action.context).toEqual({ allowed_company_ids: [1] });
    });
});
