import { Component, xml } from "@odoo/owl";
import { describe, expect, test } from "@odoo/hoot";
import { click, edit, select } from "@odoo/hoot-dom";
import { advanceTime, animationFrame } from "@odoo/hoot-mock";
import { defineModels, mockService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { registry } from "@web/core/registry";

const TAG = "mc_rov.work_center";
const ASSIGNMENT = "mc.rov.work.assignment";
const row = (id) => ({ id, reference: `Registro ${id}`, context: "Modelo QA", state: "Borrador" });
const result = (id) => ({ rows: [row(id)], total: 1, next_offset: false });
const overview = (canCreate = true) => [
    { topic: "repair", kind: "orders", available: true, count: 1, can_create: canCreate },
    { topic: "acceptance", kind: "equipment", available: true, count: 1, can_create: canCreate },
    { topic: "equipment", kind: "equipment", available: true, count: 1, can_create: canCreate },
];

function requireCenter() {
    const available = registry.category("actions").contains(TAG);
    expect(available).toBe(true, { message: "Falta la acción cliente Centro de trabajo ROV" });
    return available ? registry.category("actions").get(TAG) : null;
}

async function mountCenter(Center, props = {}) {
    return mountWithCleanup(Center, {
        props: { action: { tag: TAG }, ...props, state: { ...props.state, workCenter: { workspace: "process", ...props.state?.workCenter } } },
    });
}

class AssignmentViewProbe extends Component {
    static props = ["*"];
    static template = xml`<div data-assigned-model="" t-att-data-model="props.action.res_model"/>`;
}

describe("mc_rov assigned work", () => {
    defineModels(mailModels);

    function mockAssignment(canViewTeam = false) {
        const calls = [];
        const actions = [];
        mockService("action", { doAction: (action) => actions.push(action) });
        mockService("orm", {
            searchRead(model, domain, fields) {
                expect(model).toBe("hr.employee.public");
                expect(fields).toEqual(["display_name"]);
                return Promise.resolve([{ id: 7, display_name: "Pedro" }, { id: 8, display_name: "Ana" }]);
            },
            call(model, method, args, kwargs) {
                if (model !== ASSIGNMENT) {
                    return Promise.resolve(method === "get_overview" ? overview() : result(41));
                }
                calls.push({ method, args, kwargs });
                if (method === "get_capabilities") {
                    return Promise.resolve({ can_view_team: canViewTeam, can_coordinate: true });
                }
                if (method === "get_processes") return Promise.resolve([{ key: "all", label: "Todos los procesos", available: true }]);
                return Promise.resolve({ type: "ir.actions.act_window", views: [[false, "list"], [false, "kanban"]],
                    res_model: { action_activities: "mail.activity", action_tasks: "project.task", action_projects: "project.project" }[method],
                    context: { allowed_company_ids: [1] } });
            },
        });
        return { calls, actions };
    }

    async function openAssignedWork(props = {}) {
        const Center = requireCenter();
        if (!Center) return false;
        class CenterProbe extends Center {}
        CenterProbe.components = { ...Center.components, AssignedWorkView: AssignmentViewProbe };
        await mountCenter(CenterProbe, { ...props, state: { ...props.state,
            workCenter: { ...props.state?.workCenter, workspace: "assigned" } } });
        const present = document.querySelector('[data-work-assigned]');
        expect(Boolean(present)).toBe(true, { message: "Falta la entrada Trabajo asignado" });
        if (!present) return false;
        await animationFrame();
        return true;
    }

    test("actividades personales aloja accion nativa sin excluir futuras", async () => {
        const { calls, actions } = mockAssignment();
        if (!await openAssignedWork()) return;
        expect('[data-topic]').toHaveCount(6);
        await animationFrame();
        const call = calls.find((item) => item.method === "action_activities");
        expect(call.kwargs).toEqual({ scope: "mine", employee_id: false, process: "all" });
        expect('[data-model="mail.activity"]').toHaveCount(1);
        expect(actions).toHaveLength(0);
    });

    test("coordinacion sin consulta global no ofrece trabajo del equipo", async () => {
        mockAssignment();
        if (!await openAssignedWork()) return;
        expect('.mc_assignment_scope option[value="team"]').toHaveCount(0);
        expect('.mc_assignment_scope').toHaveValue("mine");
    });

    test("consulta global y empleado se pasan al servicio sin alterar permisos", async () => {
        const { calls } = mockAssignment(true);
        if (!await openAssignedWork()) return;
        await click('.mc_assignment_scope');
        await select("team");
        expect('.mc_assignment_scope').toHaveValue("team");
        await click('.mc_assignment_employee');
        await select("7");
        expect('.mc_assignment_employee').toHaveValue("7");
        await animationFrame();
        expect(calls.filter((item) => item.method === "action_activities").at(-1).kwargs)
            .toEqual({ scope: "team", employee_id: 7, process: "all" });
    });

    test("tareas y proyectos usan acciones separadas sin filtro de empleado", async () => {
        const { calls, actions } = mockAssignment();
        if (!await openAssignedWork()) return;
        await click('.mc_assignment_employee');
        await select("7");
        expect('.mc_assignment_employee').toHaveValue("7");
        await click('[data-assignment-kind="tasks"]');
        await animationFrame();
        expect('.mc_assignment_employee').toHaveCount(0);
        await click('[data-assignment-kind="projects"]');
        await animationFrame();
        expect('[data-model="project.project"]').toHaveCount(1);
        expect(actions).toHaveLength(0);
        expect(calls.filter((item) => ["action_tasks", "action_projects"].includes(item.method))
            .map((item) => item.kwargs)).toEqual([{ scope: "mine", process: "all" }, { scope: "mine", process: "all" }]);
    });

    test("retorno conserva empleado y revalida permiso del alcance guardado", async () => {
        const { calls } = mockAssignment(false);
        if (!await openAssignedWork({ state: { workCenter: {
            assignedWork: { scope: "team", employeeId: 8, kind: "activities" },
        } } })) return;
        expect('.mc_assignment_scope').toHaveValue("mine");
        expect('.mc_assignment_employee').toHaveValue("8");
        await animationFrame();
        expect(calls.filter((item) => item.method === "action_activities").at(-1).kwargs)
            .toEqual({ scope: "mine", employee_id: 8, process: "all" });
    });
});

describe("mc_rov work center", () => {
    // El montaje inicia servicios de Mail aunque el centro no contenga chatter.
    defineModels(mailModels);

    test("responsable muestra nombre y distingue vacio de acceso restringido", async () => {
        const Center = requireCenter();
        if (!Center) return;
        mockService("orm", {
            call(_model, method) {
                return Promise.resolve(method === "get_overview" ? overview() : {
                    rows: [
                        { ...row(41), responsible: "Usuario asignado", responsible_state: "assigned" },
                        { ...row(42), responsible: false, responsible_state: "unassigned" },
                        { ...row(43), responsible: false, responsible_state: "restricted" },
                    ], total: 3, next_offset: false, responsible_label: "Responsable",
                });
            },
        });
        await mountCenter(Center);
        expect("th.mc_work_center_responsible_heading").toHaveText("Responsable");
        expect("tbody tr:nth-child(1) .mc_work_center_responsible").toHaveText("Usuario asignado");
        expect("tbody tr:nth-child(2) .mc_work_center_responsible").toHaveText("Sin responsable");
        expect("tbody tr:nth-child(3) .mc_work_center_responsible").toHaveText("Sin acceso al nombre");
        expect(".mc_work_center_responsible a").toHaveCount(0);
    });

    test("revision en borrador dice tecnico responsable sin afirmar que ya se realizo", async () => {
        const Center = requireCenter();
        if (!Center) return;
        mockService("orm", {
            call(_model, method) {
                return Promise.resolve(method === "get_overview" ? [
                    { topic: "repair", kind: "reviews", available: true, count: 1, can_create: true },
                ] : { ...result(41), responsible_label: "Técnico responsable",
                    rows: [{ ...row(41), responsible: "Técnico de Prueba", responsible_state: "assigned" }] });
            },
        });
        await mountCenter(Center, { state: { workCenter: { topic: "repair", kind: "reviews" } } });
        expect("th.mc_work_center_responsible_heading").toHaveText("Técnico responsable");
        expect("th.mc_work_center_responsible_heading").toHaveAttribute("title", "Persona registrada como responsable de realizar la prueba.");
        expect(".mc_work_center_responsible").toHaveText("Técnico de Prueba");
    });

    test("equipo no muestra responsable y al regresar se recupera la columna correcta", async () => {
        const Center = requireCenter();
        if (!Center) return;
        mockService("orm", {
            call(_model, method, args) {
                if (method === "get_overview") return Promise.resolve(overview());
                const assigned = args[1] === "orders";
                return Promise.resolve({ ...result(41), responsible_label: assigned ? "Responsable" : false,
                    rows: [{ ...row(41), responsible: assigned ? "Usuario asignado" : false }] });
            },
        });
        await mountCenter(Center);
        expect("th.mc_work_center_responsible_heading").toHaveText("Responsable");
        await click('[data-topic="equipment"]');
        await animationFrame();
        expect("th.mc_work_center_responsible_heading").toHaveCount(0);
        await click('[data-topic="repair"]');
        await animationFrame();
        expect("th.mc_work_center_responsible_heading").toHaveText("Responsable");
    });

    test("seleccionar área consulta registros sin crear ni navegar", async () => {
        const Center = requireCenter();
        if (!Center) return;
        const calls = [];
        mockService("action", { doAction: () => calls.push("navigate") });
        mockService("orm", {
            call(_model, method) {
                calls.push(method);
                return Promise.resolve(method === "get_overview" ? overview() : result(41));
            },
        });
        await mountCenter(Center);
        await click('[data-topic="acceptance"]');
        await animationFrame();
        expect(calls.includes("get_records")).toBe(true);
        expect(calls.includes("action_create")).toBe(false);
        expect(calls.includes("navigate")).toBe(false);
    });

    test("abrir recibe la ID elegida y no pide crear", async () => {
        const Center = requireCenter();
        if (!Center) return;
        let chosen;
        const actions = [];
        mockService("action", { doAction: (action) => actions.push(action) });
        mockService("orm", {
            call(_model, method, args) {
                if (method === "get_overview") return Promise.resolve(overview());
                if (method === "get_records") return Promise.resolve(result(41));
                expect(method).toBe("action_open");
                chosen = args;
                return Promise.resolve({ type: "ir.actions.act_window", res_id: 41 });
            },
        });
        await mountCenter(Center);
        await click('[data-record-id="41"]');
        await animationFrame();
        expect(chosen).toEqual(["repair", "orders", 41]);
        expect(actions[0].res_id).toBe(41);
    });

    test("capacidad de solo lectura no ofrece creación", async () => {
        const Center = requireCenter();
        if (!Center) return;
        mockService("orm", {
            call(_model, method) {
                return Promise.resolve(method === "get_overview" ? overview(false) : result(41));
            },
        });
        await mountCenter(Center);
        expect(".mc_work_center_create").toHaveCount(0);
        expect('[data-record-id="41"]').toHaveCount(1);
    });

    test("estado restaurado conserva búsqueda modelo y consulta datos frescos", async () => {
        const Center = requireCenter();
        if (!Center) return;
        let filters;
        mockService("orm", {
            call(_model, method, args, kwargs) {
                if (method === "get_overview") return Promise.resolve(overview());
                filters = { args, kwargs };
                return Promise.resolve(result(81));
            },
        });
        await mountCenter(Center, {
            state: { workCenter: {
                topic: "equipment", kind: "equipment",
                filters: { "equipment:equipment": {
                    query: "26-02", model_id: 9, state_filter: "all", offset: 0,
                } },
            } },
        });
        expect(filters.args).toEqual(["equipment", "equipment"]);
        expect(filters.kwargs.query).toBe("26-02");
        expect(filters.kwargs.model_id).toBe(9);
        expect(".mc_work_center_search").toHaveValue("26-02");
        expect('[data-record-id="81"]').toHaveCount(1);
    });

    test("respuesta antigua no reemplaza el área seleccionada después", async () => {
        const Center = requireCenter();
        if (!Center) return;
        let resolveOld;
        const old = new Promise((resolve) => { resolveOld = resolve; });
        mockService("orm", {
            call(_model, method, args) {
                if (method === "get_overview") return Promise.resolve(overview());
                if (args[0] === "acceptance") return old;
                return Promise.resolve(result(args[0] === "equipment" ? 81 : 41));
            },
        });
        await mountCenter(Center);
        await click('[data-topic="acceptance"]');
        await animationFrame();
        await click('[data-topic="equipment"]');
        await animationFrame();
        resolveOld(result(99));
        await animationFrame();
        expect('[data-record-id="81"]').toHaveCount(1);
        expect('[data-record-id="99"]').toHaveCount(0);
    });

    test("candidatas abre su cola sin crear ni abrir lecciones", async () => {
        const Center = requireCenter();
        if (!Center) return;
        const calls = [];
        const actions = [];
        mockService("action", { doAction: (action) => actions.push(action) });
        mockService("orm", {
            call(_model, method) {
                calls.push(method);
                if (method === "get_overview") return Promise.resolve([
                    { topic: "quality", kind: "lessons", available: true, count: 0,
                        can_create: false, can_candidates: true },
                ]);
                if (method === "get_records") return Promise.resolve({ rows: [], total: 0, next_offset: false });
                return Promise.resolve({ type: "ir.actions.act_window", res_model: "mc.rov.linea.falla" });
            },
        });
        await mountCenter(Center, { state: { workCenter: { topic: "quality", kind: "lessons" } } });
        expect(".mc_work_center_candidates").toHaveCount(1);
        if (!document.querySelector(".mc_work_center_candidates")) return;
        await click(".mc_work_center_candidates");
        await animationFrame();
        expect(calls.includes("action_candidates")).toBe(true);
        expect(calls.includes("action_create")).toBe(false);
        expect(actions[0].res_model).toBe("mc.rov.linea.falla");
    });

    test("candidatas no ofrece acceso cuando falta permiso", async () => {
        const Center = requireCenter();
        if (!Center) return;
        mockService("orm", {
            call(_model, method) {
                return Promise.resolve(method === "get_overview" ? [
                    { topic: "quality", kind: "lessons", available: true, count: 0,
                        can_create: false, can_candidates: false },
                ] : { rows: [], total: 0, next_offset: false });
            },
        });
        await mountCenter(Center, { state: { workCenter: { topic: "quality", kind: "lessons" } } });
        expect(".mc_work_center_candidates").toHaveCount(0);
    });

    test("ayuda nativa conserva HTML preparado para la vista vacía", async () => {
        const Center = requireCenter();
        if (!Center) return;
        let opened;
        const html = "<p>No hay candidatas.</p>";
        const instance = {
            state: { acting: false, error: "" },
            orm: { call: async () => ({ type: "ir.actions.act_window", help: html }) },
            action: { doAction: async (action) => { opened = action; } },
        };
        await Center.prototype.navigate.call(instance, "action_candidates", []);
        expect(typeof opened.help).toBe("object");
        expect(String(opened.help)).toBe(html);
    });

    test("selector de modelo consulta unidades accesibles en lugar del catálogo de diseño", async () => {
        const Center = requireCenter();
        if (!Center) return;
        const lookups = [];
        mockService("orm", {
            call(_model, method, args, kwargs) {
                if (method === "get_overview") return Promise.resolve(overview());
                if (method === "get_records") return Promise.resolve(result(81));
                lookups.push({ method, args, kwargs });
                return Promise.resolve({ rows: [{ id: 9, reference: "ROV - Petrohue" }], total: 1 });
            },
        });
        await mountCenter(Center, { state: { workCenter: { topic: "equipment", kind: "equipment" } } });
        await click('input[placeholder="Escribe para buscar un modelo"]');
        await edit("Petrohue");
        await advanceTime(300);
        await animationFrame();
        expect(lookups[0].method).toBe("get_equipment_models");
        expect(lookups[0].kwargs.query).toBe("Petrohue");
        expect(".mc_work_center_model_options button").toHaveText("ROV - Petrohue");
    });
    test("estado operativo se envía y se conserva al cambiar de área", async () => {
        const Center = requireCenter();
        if (!Center) return;
        const calls = [];
        mockService("orm", {
            call(_model, method, args, kwargs) {
                if (method === "get_overview") return Promise.resolve(overview());
                calls.push({ args, kwargs });
                return Promise.resolve(result(41));
            },
        });
        await mountCenter(Center, { state: { workCenter: { topic: "equipment", kind: "equipment" } } });
        expect(".mc_work_center_toolbar select").toHaveCount(1);
        if (!document.querySelector(".mc_work_center_toolbar select")) return;
        await click(".mc_work_center_toolbar select");
        await select("En reparación");
        await animationFrame();
        expect(calls.at(-1).kwargs.state_filter).toBe("En reparación");
        await click('[data-topic="repair"]');
        await animationFrame();
        await click('[data-topic="equipment"]');
        await animationFrame();
        expect(calls.at(-1).kwargs.state_filter).toBe("En reparación");
        expect(".mc_work_center_toolbar select").toHaveValue("En reparación");
    });

});


describe("mc_rov inventory navigation", () => {
    defineModels(mailModels);
    const inventoryButton = '[data-topic="inventory"]';
    const native = { type: "ir.actions.act_window", res_model: "stock.quant",
        views: [[false, "list"]], context: { allowed_company_ids: [1] } };

    async function setupInventory({ available = true, failRPC = false } = {}) {
        const calls = [];
        const actions = [];
        mockService("orm", {
            async call(model, method, args, kwargs) {
                calls.push({ model, method, args, kwargs });
                if (method === "get_overview") return [...overview(),
                    { topic: "inventory", kind: "stock", available }];
                if (method === "get_inventory_destinations") return [{ key: "stock", section: "stock", label: "Existencias", available: true, can_create: false }];
                if (method === "action_inventory_destination") {
                    if (failRPC) throw new Error("Permiso retirado");
                    return native;
                }
                return result(41);
            },
        });
        mockService("action", {
            async doAction(action) {
                actions.push(action);
            },
        });
        const Center = requireCenter();
        class CenterProbe extends Center {}
        CenterProbe.components = { ...Center.components, AssignedWorkView: AssignmentViewProbe };
        const center = await mountCenter(CenterProbe, { state: { workCenter: {
            topic: "equipment", kind: "equipment", filters: {
                "equipment:equipment": { query: "Petrohue", model_id: 9,
                    model_label: "ROV Petrohue", state_filter: "En reparación", offset: 0 },
            },
        } } });
        return { center, calls, actions };
    }

    function hasInventory() {
        const present = Boolean(document.querySelector(inventoryButton));
        expect(present).toBe(true, { message: "Falta el botón Inventario autorizado" });
        return present;
    }

    test("ocho accesos en orden con etiquetas cortas", async () => {
        await setupInventory();
        expect([...document.querySelectorAll(".mc_work_center_navigation button")]
            .map((button) => button.textContent.trim())).toEqual([
            "Trabajo asignado", "Reparar", "Fabricar", "Aceptar", "Consultar equipo",
            "Calidad", "Inventario", "Diseño / BoM",
        ]);
    });

    test("sin permiso de inventario conserva los otros accesos", async () => {
        await setupInventory({ available: false });
        expect(inventoryButton).toHaveCount(0);
        expect(".mc_work_center_navigation button").toHaveCount(7);
    });

    test("abre existencias nativas y conserva filtros para volver", async () => {
        const { center, calls, actions } = await setupInventory();
        if (!hasInventory()) return;
        const saved = center.exportState();
        await click(inventoryButton);
        await animationFrame();
        expect(calls.filter((call) => call.method === "action_inventory_destination"))
            .toEqual([{ model: "mc.rov.work.center", method: "action_inventory_destination", args: ["stock"], kwargs: undefined }]);
        expect(center.state.inventoryAction).toEqual(native);
        expect(actions).toHaveLength(0);
        await click('[data-topic="equipment"]');
        await animationFrame();
        expect(center.exportState().filters).toEqual(saved.filters);
        expect(document.querySelector('[data-topic="equipment"]').classList.contains("is_selected")).toBe(true);
    });

    test("edicion pendiente impide salir hacia inventario", async () => {
        const { center, calls, actions } = await setupInventory();
        if (!hasInventory()) return;
        center.nativeView = { canLeave: async () => false };
        const saved = center.exportState();
        await click(inventoryButton);
        await animationFrame();
        expect(calls.filter((call) => call.method === "action_inventory_destination")).toHaveLength(0);
        expect(actions).toHaveLength(0);
        expect(center.exportState()).toEqual(saved);
    });

    test("permiso retirado muestra error sin perder el area", async () => {
        const { center, actions } = await setupInventory({ failRPC: true });
        if (!hasInventory()) return;
        const saved = center.exportState();
        await click(inventoryButton);
        await animationFrame();
        expect(actions).toHaveLength(0);
        expect(center.exportState().filters).toEqual(saved.filters);
        expect(document.querySelector('[role="alert"]').textContent.includes("No se pudo abrir el destino")).toBe(true);
        expect(center.state.acting).toBe(false);
    });

    test("fallo al cargar vista nativa permite reintentar sin cambiar filtros", async () => {
        const { center } = await setupInventory();
        if (!hasInventory()) return;
        const saved = center.exportState();
        await click(inventoryButton);
        await animationFrame();
        center.inventoryFailed();
        await animationFrame();
        expect(center.exportState().filters).toEqual(saved.filters);
        expect(document.querySelector('[role="alert"]').textContent.includes("No se pudo abrir el destino")).toBe(true);
        expect(center.state.acting).toBe(false);
    });

    test("doble apertura no solicita dos acciones de inventario", async () => {
        const { center, calls, actions } = await setupInventory();
        if (!hasInventory()) return;
        await Promise.all([center.selectTopic("inventory"), center.selectTopic("inventory")]);
        await animationFrame();
        expect(calls.filter((call) => call.method === "action_inventory_destination")).toHaveLength(1);
        expect(actions).toHaveLength(0);
    });

    test("menu usa dos cuatro u ocho columnas segun su contenedor", async () => {
        await setupInventory();
        if (!hasInventory()) return;
        const inner = document.querySelector(".mc_work_center_inner");
        const nav = inner.querySelector(".mc_work_center_navigation");
        for (const [width, columns] of [[320, 2], [480, 2], [1000, 4], [1600, 8], [480, 2]]) {
            inner.style.width = `${width}px`;
            await animationFrame();
            const boxes = [...nav.querySelectorAll("button")].map((button) => button.getBoundingClientRect());
            const firstRow = boxes.filter((box) => Math.abs(box.top - boxes[0].top) < 1);
            expect(firstRow.length).toBe(columns);
            expect(new Set(boxes.map((box) => Math.round(box.top))).size).toBe(8 / columns);
            expect(boxes.every((box) => Math.abs(box.width - boxes[0].width) < 1)).toBe(true);
            expect(nav.scrollWidth <= nav.clientWidth + 1).toBe(true);
        }
    });
});

describe("mc_rov inventory workspace", () => {
    defineModels(mailModels);
    const entries = () => [
        ["stock", "stock", "Existencias"], ["products", "products", "Productos"],
        ["variants", "products", "Variantes"], ["lots", "lots", "Series y lotes"],
        ["receipts", "operations", "Recepciones"], ["deliveries", "operations", "Entregas"],
        ["internal", "operations", "Traslados internos"], ["counts", "operations", "Conteos y ajustes"],
        ["replenishment", "replenishment", "Reabastecimiento"],
    ].map(([key, section, label]) => ({ key, section, label, available: true, can_create: false }));
    const models = { stock: "stock.quant", products: "product.template", variants: "product.product",
        lots: "stock.lot", receipts: "stock.picking", deliveries: "stock.picking",
        internal: "stock.picking", counts: "stock.quant", replenishment: "stock.warehouse.orderpoint" };
    const native = (key) => ({ type: "ir.actions.act_window", res_model: models[key],
        views: [[false, "list"], [false, "kanban"]], domain: [["company_id", "in", [1, false]]],
        context: { allowed_company_ids: [1], search_default_goods: 1, default_is_storable: true } });

    class InventoryProbe extends Component {
        static props = ["*"];
        static template = xml`<div data-inventory-model="" t-att-data-model="props.action.res_model"
            t-att-data-saved="saved" t-att-data-view="props.viewType"/>`;
        get saved() { return JSON.stringify(this.props.saved || {}); }
    }

    async function setupWorkspace(options = {}) {
        const calls = [], actions = [], selectedMenus = [];
        const controls = { failCapabilities: false, failDestination: false, ...options };
        mockService("orm", {
            async call(model, method, args = [], kwargs = {}) {
                calls.push({ model, method, args, kwargs });
                if (method === "get_overview") return [...overview(),
                    { topic: "inventory", kind: "stock", available: true }];
                if (method === "get_inventory_destinations") {
                    if (controls.failCapabilities) throw new Error("Sin conexión");
                    return controls.entries || entries();
                }
                if (method === "action_inventory_destination") {
                    if (controls.failDestination) throw new Error("Permiso retirado");
                    return controls.destination ? controls.destination(args[0]) : native(args[0]);
                }
                if (method === "get_inventory_application") return controls.application ? controls.application() : { menu_id: 129 };
                if (method === "action_inventory") return native("stock");
                return result(41);
            },
        });
        mockService("action", { async doAction(action) { actions.push(action); } });
        const app = { id: 129, appID: 129, actionID: 900, name: "Inventario" };
        mockService("menu", { getApps: () => [app], getMenu: (id) => id === 129 ? app : null,
            async selectMenu(menu) { selectedMenus.push(typeof menu === "number" ? menu : menu.id); } });
        const Center = requireCenter();
        class CenterProbe extends Center {}
        class RegisteredInventoryProbe extends InventoryProbe {
            setup() { controls.viewProps = this.props; }
        }
        CenterProbe.components = { ...Center.components, AssignedWorkView: RegisteredInventoryProbe };
        const center = await mountCenter(CenterProbe, { state: { workCenter: {
            topic: "equipment", kind: "equipment", filters: {
                "equipment:equipment": { query: "Repuesto", state_filter: "all", offset: 0 },
            }, ...options.saved,
        }, ...options.localState } });
        return { center, calls, actions, selectedMenus, controls };
    }

    async function openWorkspace() {
        await click('[data-topic="inventory"]');
        await animationFrame();
        const present = Boolean(document.querySelector('[data-inventory-workspace]'));
        expect(present).toBe(true, { message: "Falta el espacio operativo de Inventario" });
        return present;
    }
    async function section(key) {
        await click(`[data-inventory-section="${key}"]`);
        await animationFrame();
    }
    async function destination(key) {
        await click(`[data-inventory-destination="${key}"]`);
        await animationFrame();
    }

    test("Inventario abre cinco secciones dentro del Centro", async () => {
        const { actions } = await setupWorkspace();
        if (!await openWorkspace()) return;
        expect([...document.querySelectorAll('[data-inventory-section]')].map((el) => el.textContent.trim()))
            .toEqual(["Existencias", "Productos", "Series y lotes", "Operaciones", "Reabastecimiento"]);
        expect('[data-topic="inventory"].is_selected').toHaveCount(1);
        expect(actions).toHaveLength(0);
    });
    test("Productos ofrece productos y variantes sin limitar a ROV", async () => {
        await setupWorkspace();
        if (!await openWorkspace()) return;
        await section("products");
        expect('[data-inventory-destination="products"]').toHaveCount(1);
        expect('[data-inventory-destination="variants"]').toHaveCount(1);
        expect('[data-inventory-model]').toHaveAttribute("data-model", "product.template");
    });
    test("Operaciones abre cuatro destinos nativos separados", async () => {
        const { calls } = await setupWorkspace();
        if (!await openWorkspace()) return;
        await section("operations");
        for (const key of ["receipts", "deliveries", "internal", "counts"]) {
            await destination(key);
            expect('[data-inventory-model]').toHaveAttribute("data-model", models[key]);
            expect(calls.filter((call) => call.method === "action_inventory_destination").at(-1).args).toEqual([key]);
        }
    });
    test("destinos no permitidos no se pueden abrir", async () => {
        const { calls } = await setupWorkspace({ entries: entries().map((entry) =>
            ({ ...entry, available: entry.key !== "variants" && entry.key !== "replenishment" })) });
        if (!await openWorkspace()) return;
        await section("products");
        const button = document.querySelector('[data-inventory-destination="variants"]');
        expect(!button || button.disabled).toBe(true);
        expect(calls.some((call) => call.method === "action_inventory_destination" && call.args[0] === "variants")).toBe(false);
        const replenish = document.querySelector('[data-inventory-section="replenishment"]');
        expect(!replenish || replenish.disabled).toBe(true);
    });
    test("vista nativa recibe defaults dominio y vistas sin inventar permisos", async () => {
        const { center, actions } = await setupWorkspace();
        if (!await openWorkspace()) return;
        await section("products");
        expect(center.state.inventoryAction).toEqual(native("products"));
        expect(actions).toHaveLength(0);
    });
    test("edicion pendiente bloquea cambiar de area", async () => {
        const { center } = await setupWorkspace();
        if (!await openWorkspace()) return;
        center.nativeView = { canLeave: async () => false };
        await click('[data-topic="repair"]');
        expect('[data-inventory-workspace]').toHaveCount(1);
    });
    test("edicion pendiente bloquea cambiar de destino", async () => {
        const { center, calls } = await setupWorkspace();
        if (!await openWorkspace()) return;
        center.nativeView = { canLeave: async () => false };
        const before = calls.length;
        await section("products");
        expect(calls.slice(before).some((call) => call.method === "action_inventory_destination")).toBe(false);
        expect('[data-inventory-model]').toHaveAttribute("data-model", "stock.quant");
    });
    test("cada destino conserva su busqueda nativa al volver", async () => {
        const { center } = await setupWorkspace();
        if (!await openWorkspace()) return;
        const saved = { globalState: { searchModel: { searchItems: { qa: "Filtro guardado" } } } };
        center.nativeView = { canLeave: async () => true, snapshot: () => saved };
        await section("products");
        center.nativeView = null;
        await section("stock");
        expect(JSON.parse(document.querySelector('[data-inventory-model]').dataset.saved)).toEqual(saved);
    });
    test("Inventario completo selecciona aplicacion y menus autorizados", async () => {
        const { selectedMenus, actions } = await setupWorkspace();
        if (!await openWorkspace()) return;
        await click('[data-inventory-full]');
        await animationFrame();
        expect(selectedMenus).toEqual([129]);
        expect(actions).toHaveLength(0);
    });
    test("edicion pendiente bloquea abrir aplicacion completa", async () => {
        const { center, selectedMenus } = await setupWorkspace();
        if (!await openWorkspace()) return;
        center.nativeView = { canLeave: async () => false };
        await click('[data-inventory-full]');
        expect(selectedMenus).toHaveLength(0);
    });
    test("error de capacidades permite reintentar", async () => {
        const { controls } = await setupWorkspace({ failCapabilities: true });
        if (!await openWorkspace()) return;
        expect('[data-inventory-retry]').toHaveCount(1);
        controls.failCapabilities = false;
        await click('[data-inventory-retry]');
        await animationFrame();
        expect('[data-inventory-model]').toHaveAttribute("data-model", "stock.quant");
    });
    test("permiso retirado muestra error y permite reintentar destino", async () => {
        const { controls } = await setupWorkspace();
        if (!await openWorkspace()) return;
        controls.failDestination = true;
        await section("lots");
        expect('[data-inventory-retry]').toHaveCount(1);
        expect('[data-inventory-model]').toHaveCount(0);
        controls.failDestination = false;
        await click('[data-inventory-retry]');
        await animationFrame();
        expect('[data-inventory-model]').toHaveAttribute("data-model", "stock.lot");
    });
    test("respuesta tardia no reemplaza el destino seleccionado despues", async () => {
        let release;
        const { controls } = await setupWorkspace();
        if (!await openWorkspace()) return;
        controls.destination = (key) => key === "products"
            ? new Promise((resolve) => { release = () => resolve(native(key)); }) : native(key);
        await section("products");
        await section("lots");
        release();
        await animationFrame();
        expect('[data-inventory-model]').toHaveAttribute("data-model", "stock.lot");
    });
    test("doble seleccion en carga solicita un solo destino", async () => {
        let release;
        const { controls, calls } = await setupWorkspace();
        if (!await openWorkspace()) return;
        controls.destination = (key) => new Promise((resolve) => { release = () => resolve(native(key)); });
        await section("products");
        await section("products");
        expect(calls.filter((call) => call.method === "action_inventory_destination" && call.args[0] === "products")).toHaveLength(1);
        release();
        await animationFrame();
    });
    test("retorno restaura destino guardado y revalida capacidades", async () => {
        const { calls } = await setupWorkspace({ saved: { inventory: { section: "products", destination: "variants", viewType: "list" } } });
        if (!await openWorkspace()) return;
        expect('[data-inventory-model]').toHaveAttribute("data-model", "product.product");
        expect(calls.some((call) => call.method === "get_inventory_destinations")).toBe(true);
    });
    test("destino guardado sin permiso se sustituye por uno permitido", async () => {
        await setupWorkspace({ saved: { inventory: { section: "products", destination: "variants" } },
            entries: entries().map((entry) => ({ ...entry, available: entry.key !== "variants" })) });
        if (!await openWorkspace()) return;
        expect('[data-inventory-model]').toHaveAttribute("data-model", "product.template");
    });
    test("volver a equipo conserva filtro previo al inventario", async () => {
        const { center } = await setupWorkspace();
        const before = center.exportState().filters;
        if (!await openWorkspace()) return;
        await click('[data-topic="equipment"]');
        await animationFrame();
        expect(center.exportState().filters).toEqual(before);
        expect('.mc_work_center_search').toHaveValue("Repuesto");
    });
    test("selector usa tipos de vista ofrecidos por accion nativa", async () => {
        await setupWorkspace();
        if (!await openWorkspace()) return;
        await click('[data-inventory-view="kanban"]');
        await animationFrame();
        expect('[data-inventory-model]').toHaveAttribute("data-view", "kanban");
        expect('[data-inventory-view="calendar"]').toHaveCount(0);
    });
    test("fallo de vista nativa muestra reintento y retira contenido anterior", async () => {
        const { controls } = await setupWorkspace();
        if (!await openWorkspace()) return;
        controls.viewProps.onError();
        await animationFrame();
        expect('[data-inventory-model]').toHaveCount(0);
        expect('[data-inventory-retry]').toHaveCount(1);
        await click('[data-inventory-retry]');
        await animationFrame();
        expect('[data-inventory-model]').toHaveAttribute("data-model", "stock.quant");
    });
    test("cambio de empresa descarta estado nativo de la seleccion anterior", async () => {
        const { center, controls } = await setupWorkspace();
        if (!await openWorkspace()) return;
        const saved = { globalState: { context: { allowed_company_ids: [1] } } };
        center.nativeView = { canLeave: async () => true, snapshot: () => saved };
        await section("products");
        center.nativeView = null;
        controls.destination = (key) => ({ ...native(key), context: { allowed_company_ids: [2] } });
        await section("stock");
        expect(center.state.inventoryAction.context.allowed_company_ids).toEqual([2]);
        expect(JSON.parse(document.querySelector('[data-inventory-model]').dataset.saved)).toEqual({});
    });
    test("actualizar conserva busqueda pero descarta cache local de Inventario", async () => {
        const { center } = await setupWorkspace();
        if (!await openWorkspace()) return;
        const globalState = { searchModel: { query: "Filtro guardado" } };
        center.nativeView = { canLeave: async () => true,
            snapshot: () => ({ globalState, state: { cachedRecords: "Datos anteriores" } }) };
        await center.refresh();
        await animationFrame();
        expect(JSON.parse(document.querySelector('[data-inventory-model]').dataset.saved)).toEqual({ globalState });
    });
    test("ultima seleccion gana aunque las confirmaciones de salida terminen al reves", async () => {
        const { center } = await setupWorkspace();
        if (!await openWorkspace()) return;
        const guards = [];
        center.nativeView = { canLeave: () => new Promise((resolve) => guards.push(resolve)), snapshot: () => ({}) };
        const first = center.changeInventorySection("products");
        const last = center.changeInventorySection("lots");
        guards[1](true);
        await last;
        guards[0](true);
        await first;
        await animationFrame();
        expect('[data-inventory-model]').toHaveAttribute("data-model", "stock.lot");
    });
    test("confirmacion antigua no abre un destino despues de salir de Inventario", async () => {
        const { center, calls } = await setupWorkspace();
        if (!await openWorkspace()) return;
        const guards = [];
        center.nativeView = { canLeave: () => new Promise((resolve) => guards.push(resolve)), snapshot: () => ({}) };
        const old = center.changeInventorySection("products");
        const leave = center.selectTopic("repair");
        guards[1](true);
        await leave;
        guards[0](true);
        await old;
        expect(calls.some((call) => call.method === "action_inventory_destination" && call.args[0] === "products")).toBe(false);
        expect(center.state.workspace).toBe("process");
    });
    test("respuesta antigua de aplicacion completa no redirige tras cambiar de area", async () => {
        const { center, controls, selectedMenus } = await setupWorkspace();
        if (!await openWorkspace()) return;
        let release;
        controls.application = () => new Promise((resolve) => { release = resolve; });
        const pending = center.openInventoryApplication();
        await animationFrame();
        await center.selectTopic("repair");
        release({ menu_id: 129 });
        await pending;
        expect(selectedMenus).toHaveLength(0);
    });
});
