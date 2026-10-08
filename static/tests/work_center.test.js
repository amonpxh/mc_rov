import { describe, expect, test } from "@odoo/hoot";
import { click, edit, select } from "@odoo/hoot-dom";
import { advanceTime, animationFrame } from "@odoo/hoot-mock";
import { defineModels, mockService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { registry } from "@web/core/registry";

const TAG = "mc_rov.work_center";
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
        props: { action: { tag: TAG }, ...props },
    });
}

describe("mc_rov work center", () => {
    // El montaje inicia servicios de Mail aunque el centro no contenga chatter.
    defineModels(mailModels);

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
