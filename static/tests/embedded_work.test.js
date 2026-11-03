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
    { key: "inventory", label: "Inventario", available: false, hint: "Sin acceso a operaciones" },
    { key: "all", label: "Todos los procesos", available: true, hint: "" },
    { key: "repair", label: "Reparación", available: true, hint: "" },
    { key: "manufacturing", label: "Fabricación", available: true, hint: "" },
    { key: "acceptance", label: "Aceptación", available: false, hint: "Sin actividades específicas" },
    { key: "equipment", label: "Equipo", available: true, hint: "" },
    { key: "none", label: "Sin proceso vinculado", available: true, hint: "" },
];

function mockWork({ failFirst = false, acceptanceAvailable = false, inventoryAvailable = false } = {}) {
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
                if (option.key === "inventory") {
                    const available = inventoryAvailable && kwargs.kind === "activities";
                    return { ...option, available, hint: available ? "" : option.hint };
                }
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

    test("inventario conserva busqueda empleado y alcance al actualizar", async () => {
        const Center = requireIntegration();
        if (!Center) return;
        class InventoryRefreshProbe extends Component {
            static props = ["*"];
            static template = xml`<div data-inventory-refresh="">
                <span t-esc="props.saved.globalState?.searchModel || 'Sin búsqueda'"/>
            </div>`;
            setup() {
                this.props.register(this);
                onWillUnmount(() => this.props.register(null, this));
            }
            canLeave() { return true; }
            snapshot() { return { globalState: { searchModel: "QA inventario" }, state: { modelState: { offset: 40 } } }; }
        }
        class InventoryCenter extends Center {}
        InventoryCenter.components = { ...Center.components, AssignedWorkView: InventoryRefreshProbe };
        const { calls } = mockWork({ inventoryAvailable: true });
        await mountWithCleanup(InventoryCenter, { props: { action: { tag: "mc_rov.work_center" } } });
        await choose('.mc_assignment_scope', "team");
        await choose('.mc_assignment_employee', "7");
        await choose('.mc_assignment_process', "inventory");
        await click('button[aria-label="Actualizar registros"]');
        await animationFrame();
        expect('.mc_assignment_scope').toHaveValue("team");
        expect('.mc_assignment_employee').toHaveValue("7");
        expect('.mc_assignment_process').toHaveValue("inventory");
        expect('[data-inventory-refresh]').toHaveCount(1);
        expect('[data-inventory-refresh]').toHaveText("QA inventario");
        expect('.mc_work_center_table').toHaveCount(0);
        expect(calls.filter(x => x.method === "action_activities").at(-1).kwargs)
            .toEqual({ scope: "team", employee_id: 7, process: "inventory" });
    });

    test("volver de registros conserva inventario y una sola zona de contenido", async () => {
        const Center = requireIntegration();
        if (!Center) return;
        mockWork({ inventoryAvailable: true });
        await mountWithCleanup(Center, { props: { action: { tag: "mc_rov.work_center" } } });
        await choose('.mc_assignment_scope', "team");
        await choose('.mc_assignment_employee', "7");
        await choose('.mc_assignment_process', "inventory");
        await click('[data-assignment-view="list"]');
        await click('[data-topic="acceptance"]');
        await animationFrame();
        expect('[data-native-view]').toHaveCount(0);
        expect('.mc_work_center_table').toHaveCount(1);
        await click('[data-work-assigned]');
        await animationFrame();
        expect('.mc_assignment_process').toHaveValue("inventory");
        expect('.mc_assignment_scope').toHaveValue("team");
        expect('.mc_assignment_employee').toHaveValue("7");
        expect('[data-native-view]').toHaveCount(1);
        expect('[data-native-view]').toHaveText("list");
        expect('.mc_work_center_table').toHaveCount(0);
    });

    test("inventario sin acceso descarta seleccion guardada y no solicita sus actividades", async () => {
        const Center = requireIntegration();
        if (!Center) return;
        const { calls } = mockWork({ inventoryAvailable: false });
        await mountWithCleanup(Center, { props: { action: { tag: "mc_rov.work_center" },
            state: { workCenter: { workspace: "assigned", assignedWork: {
                kind: "activities", scope: "mine", process: "inventory", employeeId: false,
            } } } } });
        await animationFrame();
        expect('.mc_assignment_process option[value="inventory"]').toHaveCount(1);
        expect('.mc_assignment_process option[value="inventory"]').not.toBeEnabled();
        expect('.mc_assignment_process').toHaveValue("all");
        expect(calls.filter(x => x.method === "action_activities").length > 0).toBe(true);
        expect(calls.filter(x => x.method === "action_activities" && x.kwargs.process === "inventory")).toHaveLength(0);
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

// Actual Mail components and their native callbacks: no substitute renderer.
import { Activity as CompletionChatter } from "@mail/core/web/activity";
import { ActivityListPopoverItem as CompletionItem } from "@mail/core/web/activity_list_popover_item";
import { ActivityMarkAsDone as CompletionDone } from "@mail/core/web/activity_markasdone_popover";
import { Activity as CompletionRecord } from "@mail/core/common/activity_model";
import { ActivityCalendarCommonPopover as CompletionCalendar } from "@mail/views/web/calendar/calendar_common/activity_calendar_common_popover";
import { ActivityCalendarYearPopover as CompletionYear } from "@mail/views/web/calendar/calendar_year/activity_calendar_year_popover";
import { ArchiveDisabledListController as CompletionNativeList } from "@mail/views/web/list/archive_disabled_list_controller";
import { onRpc as completionRpc } from "@web/../tests/web_test_helpers";
import { start as completionStart } from "@mail/../tests/mail_test_helpers";

function completionActivity(automatic) {
    return {
        id: 903,
        active: true,
        mc_automatic_pending: automatic,
        can_write: true,
        res_model: "repair.order",
        res_id: 904,
        res_name: "QA-REAL-904",
        summary: "QA trabajo pendiente",
        activity_type_id: { id: 1, name: "QA actividad" },
        activity_category: "default",
        chaining_type: "suggest",
        state: "planned",
        date_deadline: luxon.DateTime.now().plus({ days: 1 }),
        dateDeadlineFormatted: "QA fecha",
        user_id: false,
        icon: "fa-wrench",
        mail_template_ids: [],
        attachment_ids: [],
        isNoteEmpty: true,
        feedback: "",
    };
}

function completionCallbacks(automatic) {
    const calls = [];
    const activity = {
        ...completionActivity(automatic),
        remove: () => calls.push("remove"),
        markAsDone: async () => calls.push("done"),
        markAsDoneAndScheduleNext: async () => { calls.push("next"); },
    };
    const thread = { fetchNewMessages: async () => calls.push("fetch") };
    const context = {
        props: {
            activity,
            onActivityChanged: () => calls.push("changed"),
            onClickDoneAndScheduleNext: () => calls.push("schedule"),
            close: () => calls.push("close"),
        },
        thread,
        env: { services: {
            orm: { unlink: async () => calls.push("rpc-unlink") },
            "mail.store": { Thread: { insert: () => { calls.push("thread"); return thread; } } },
        } },
    };
    return { calls, context };
}

function completionList(flags, domainSelected = false) {
    const present = registry.category("views").contains("mc_automatic_activity_list");
    expect(present).toBe(true, { message: "Missing automatic list selection controller" });
    if (!present) return null;
    const Controller = registry.category("views").get("mc_automatic_activity_list").Controller;
    const controller = Object.create(Controller.prototype);
    controller.model = { root: {
        selection: flags.map((flag, index) => ({ resId: index + 1, data: { mc_automatic_pending: flag } })),
        isDomainSelected: domainSelected,
        evalContext: { context: {} },
    } };
    controller.activeActions = { delete: true, duplicate: true };
    controller.archiveEnabled = false;
    return { Controller, controller };
}

class CompletionCalendarFooter extends CompletionCalendar {
    static template = "mail.ActivityCalendarCommonPopover.footer";
}

describe("mc_rov automatic completion", () => {
    defineModels(mailModels);

    async function mountCompletion(ComponentClass, automatic, extra = {}) {
        const env = await completionStart();
        const target = document.createElement("div");
        target.dataset.mcCompletionProbe = "";
        env.target.appendChild(target);
        const props = { activity: completionActivity(automatic), onActivityChanged: () => {} };
        if (ComponentClass === CompletionChatter) props.reloadParentView = () => {};
        if (ComponentClass === CompletionItem) props.onClickEditActivityButton = () => {};
        if (ComponentClass === CompletionDone) props.close = () => {};
        return mountWithCleanup(ComponentClass, { env, target, props: { ...props, ...extra } });
    }

    async function mountCompletionCalendar(automatic) {
        const env = await completionStart();
        const target = document.createElement("div");
        target.dataset.mcCompletionProbe = "";
        env.target.appendChild(target);
        return mountWithCleanup(CompletionCalendarFooter, { env, target, props: {
            close: () => {},
            record: { id: 903, rawRecord: { id: 903, mc_automatic_pending: automatic } },
            model: { resModel: "mail.activity", load: () => {} },
            createRecord: () => {}, deleteRecord: () => {}, editRecord: () => {},
        } });
    }

    test("lista permite cierre para seleccion exclusivamente manual", () => {
        const probe = completionList([false, false]);
        if (probe) expect(probe.controller.canCloseSelection).toBe(true);
    });
    test("lista oculta cierre para seleccion automatica", () => {
        const probe = completionList([true]);
        if (probe) expect(probe.controller.canCloseSelection).toBe(false);
    });
    test("lista oculta cierre para seleccion mixta", () => {
        const probe = completionList([false, true]);
        if (probe) expect(probe.controller.canCloseSelection).toBe(false);
    });
    test("lista no supone manuales los registros no cargados del dominio", () => {
        const probe = completionList([false], true);
        if (probe) expect(probe.controller.canCloseSelection).toBe(false);
    });
    test("lista no ofrece cierre sin seleccion", () => {
        const probe = completionList([]);
        if (probe) expect(probe.controller.canCloseSelection).toBe(false);
    });
    test("lista conserva controlador nativo sin archivar", () => {
        const probe = completionList([false]);
        if (probe) expect(probe.Controller.prototype instanceof CompletionNativeList).toBe(true);
    });
    test("menu eliminar se oculta para mezcla y se conserva para manuales", () => {
        const probe = completionList([false, true]);
        if (!probe) return;
        expect(probe.controller.getStaticActionMenuItems().delete.isAvailable()).toBe(false);
        probe.controller.model.root.selection.pop();
        expect(probe.controller.getStaticActionMenuItems().delete.isAvailable()).toBe(true);
    });
    test("menu eliminar nunca concede un permiso nativo ausente", () => {
        const probe = completionList([false]);
        if (!probe) return;
        probe.controller.activeActions.delete = false;
        expect(probe.controller.getStaticActionMenuItems().delete.isAvailable()).toBe(false);
    });
    test("modificador nativo de cabecera oculta el cierre de mezcla", () => {
        const probe = completionList([false, true]);
        if (probe) expect(probe.controller.evalViewModifier("context.get('mc_automatic_close_forbidden', False)")).toBe(true);
    });
    test("modificador nativo de cabecera conserva cierre manual", () => {
        const probe = completionList([false]);
        if (probe) expect(probe.controller.evalViewModifier("context.get('mc_automatic_close_forbidden', False)")).toBe(false);
    });
    test("chatter automatico sin Hecho Cancelar ni Abrir duplicado", async () => {
        await mountCompletion(CompletionChatter, true);
        expect(".o-mail-Activity-markDone").toHaveCount(0);
        expect(".o-mail-Activity button.btn-danger").toHaveCount(0);
        expect(".o_mc_activity_open").toHaveCount(0);
        expect(".o-mail-Activity-edit").toHaveCount(1);
    });
    test("chatter manual conserva Hecho y Cancelar", async () => {
        await mountCompletion(CompletionChatter, false);
        expect(".o-mail-Activity-markDone").toHaveCount(1);
        expect(".o-mail-Activity button.btn-danger").toHaveCount(1);
    });
    test("referencia del chatter automatico abre documento sin cerrar", async () => {
        const calls = [];
        completionRpc("mail.activity", "action_open_document", ({ args }) => {
            calls.push(args);
            return { type: "ir.actions.act_window", res_model: "repair.order", res_id: 904 };
        });
        mockService("action", { doAction: (action) => calls.push(action) });
        await mountCompletion(CompletionChatter, true);
        calls.length = 0;
        expect(".o-mail-Activity .o_mc_activity_reference").toHaveCount(1);
        if (!document.querySelector(".o-mail-Activity .o_mc_activity_reference")) return;
        await click(".o-mail-Activity .o_mc_activity_reference");
        await animationFrame();
        expect(calls.length).toBe(2);
        expect(calls[1].res_id).toBe(904);
    });
    test("callback Cancelar del chatter no retira automaticas", async () => {
        const { context, calls } = completionCallbacks(true);
        await CompletionChatter.prototype.unlink.call(context);
        expect(calls).toEqual([]);
    });
    test("popover automatico sin cierre con edicion conservada", async () => {
        await mountCompletion(CompletionItem, true);
        expect(".o-mail-ActivityListPopoverItem-markAsDone").toHaveCount(0);
        expect(".o-mail-ActivityListPopoverItem-cancel").toHaveCount(0);
        expect(".o-mail-ActivityListPopoverItem-editbtn").toHaveCount(1);
    });
    test("popover manual conserva ambos cierres", async () => {
        await mountCompletion(CompletionItem, false);
        expect(".o-mail-ActivityListPopoverItem-markAsDone").toHaveCount(1);
        expect(".o-mail-ActivityListPopoverItem-cancel").toHaveCount(1);
    });
    test("referencia del popover automatico abre documento", async () => {
        const calls = [];
        completionRpc("mail.activity", "action_open_document", () => ({
            type: "ir.actions.act_window", res_model: "repair.order", res_id: 904,
        }));
        mockService("action", { doAction: (action) => calls.push(action) });
        await mountCompletion(CompletionItem, true);
        calls.length = 0;
        expect(".o-mail-ActivityListPopoverItem .o_mc_activity_reference").toHaveCount(1);
        if (!document.querySelector(".o-mail-ActivityListPopoverItem .o_mc_activity_reference")) return;
        await click(".o-mail-ActivityListPopoverItem .o_mc_activity_reference");
        await animationFrame();
        expect(calls.map((action) => action.res_id)).toEqual([904]);
    });
    test("callback Cancelar del popover no retira automaticas", async () => {
        const { context, calls } = completionCallbacks(true);
        await CompletionItem.prototype.unlink.call(context);
        expect(calls).toEqual([]);
    });
    test("formulario de cierre automatico no ofrece Hecho ni siguiente", async () => {
        await mountCompletion(CompletionDone, true);
        expect('[aria-label="Done"]').toHaveCount(0);
        expect('[aria-label="Done and Schedule Next"]').toHaveCount(0);
        expect(document.querySelector(".o-mail-ActivityMarkAsDone textarea").readOnly).toBe(true);
    });
    test("formulario de cierre manual conserva Hecho y siguiente", async () => {
        await mountCompletion(CompletionDone, false);
        expect('[aria-label="Done"]').toHaveCount(1);
        expect('[aria-label="Done and Schedule Next"]').toHaveCount(1);
        expect(document.querySelector(".o-mail-ActivityMarkAsDone textarea").readOnly).toBe(false);
    });
    test("callback Hecho automatico no envia cierre ni refresca como resuelto", async () => {
        const { context, calls } = completionCallbacks(true);
        await CompletionDone.prototype.onClickDone.call(context);
        expect(calls).toEqual([]);
    });
    test("callback Hecho y siguiente automatico no programa otra tarea", async () => {
        const { context, calls } = completionCallbacks(true);
        await CompletionDone.prototype.onClickDoneAndScheduleNext.call(context);
        expect(calls).toEqual([]);
    });
    test("calendario automatico no agrega otro boton Abrir", async () => {
        await mountCompletionCalendar(true);
        expect("[data-mc-completion-probe] button").toHaveCount(0);
    });
    test("calendario manual conserva su apertura nativa", async () => {
        const calls = [];
        completionRpc("mail.activity", "action_open_document", () => ({
            type: "ir.actions.act_window", res_model: "repair.order", res_id: 904,
        }));
        mockService("action", { doAction: (action) => calls.push(action) });
        await mountCompletionCalendar(false);
        calls.length = 0;
        expect("[data-mc-completion-probe] button").toHaveCount(1);
        await click("[data-mc-completion-probe] button");
        await animationFrame();
        expect(calls.map((action) => action.res_id)).toEqual([904]);
    });
    test("calendario anual conserva apertura nativa de la referencia", async () => {
        const calls = [];
        const context = {
            orm: { call: async (model, method, args) => {
                calls.push({ model, method, args });
                return { res_model: "repair.order", res_id: 904 };
            } },
            actionService: { doAction: (action) => calls.push(action) },
            props: { model: { load: () => {} }, close: () => {} },
        };
        await CompletionYear.prototype.onRecordClick.call(context, { rawRecord: { id: 903 } });
        expect(calls[0]).toEqual({ model: "mail.activity", method: "action_open_document", args: [903] });
        expect(calls[1].res_id).toBe(904);
    });
    test("modelo Mail rechaza cierre automatico antes de RPC y difusion", async () => {
        const calls = [];
        const context = { ...completionActivity(true), store: {
            env: { services: { orm: { call: async (...args) => calls.push(args) } } },
            activityBroadcastChannel: { postMessage: () => calls.push("broadcast") },
        } };
        await CompletionRecord.prototype.markAsDone.call(context);
        expect(calls).toEqual([]);
    });
    test("modelo Mail conserva RPC y difusion del cierre manual", async () => {
        const calls = [];
        const context = { ...completionActivity(false), store: {
            env: { services: { orm: { call: async (...args) => calls.push(args) } } },
            activityBroadcastChannel: { postMessage: () => calls.push("broadcast") },
        } };
        await CompletionRecord.prototype.markAsDone.call(context);
        expect(calls[0][0]).toBe("mail.activity");
        expect(calls[0][1]).toBe("action_feedback");
        expect(calls[1]).toBe("broadcast");
    });
    test("modelo Mail no cierra ni encadena automaticas", async () => {
        const calls = [];
        const context = { ...completionActivity(true), store: {
            env: { services: { orm: { call: async (...args) => calls.push(args) } } },
            activityBroadcastChannel: { postMessage: () => calls.push("broadcast") },
        } };
        await CompletionRecord.prototype.markAsDoneAndScheduleNext.call(context);
        expect(calls).toEqual([]);
    });
});
