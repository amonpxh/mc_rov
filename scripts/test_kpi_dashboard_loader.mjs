import assert from "node:assert/strict";
import test from "node:test";

let Loader = null;
try {
    ({ DashboardLoader: Loader } = await import("../static/src/kpi_dashboard/loader.js"));
} catch (error) {
    if (error.code !== "ERR_MODULE_NOT_FOUND") throw error;
}
const deferred = () => {
    let resolve, reject;
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
};
function setup() {
    assert.ok(Loader, "Falta el cargador protegido del tablero");
    const state = { report: { old: true }, loading: false, error: "" };
    const requests = [];
    const company = { key: "1" };
    const loader = new Loader(state, () => {
        const request = deferred();
        requests.push(request);
        return request.promise;
    }, () => company.key);
    return { state, requests, company, loader };
}

test("cargar borra cifras anteriores mientras consulta", async () => {
    const { loader, state, requests } = setup();
    const task = loader.load();
    assert.equal(state.report, null);
    assert.equal(state.loading, true);
    requests[0].resolve({ current: true });
    await task;
    assert.deepEqual(state.report, { current: true });
    assert.equal(state.loading, false);
});

test("respuesta antigua no sustituye una más reciente", async () => {
    const { loader, state, requests } = setup();
    const first = loader.load();
    const second = loader.load();
    requests[1].resolve({ version: 2 });
    await second;
    requests[0].resolve({ version: 1 });
    await first;
    assert.deepEqual(state.report, { version: 2 });
});

test("cambio de empresa invalida la respuesta en vuelo", async () => {
    const { loader, state, requests, company } = setup();
    const task = loader.load();
    company.key = "2";
    requests[0].resolve({ privateCompany: 1 });
    await task;
    assert.equal(state.report, null);
    assert.equal(state.loading, false);
});

test("un error RPC no expone el texto privado del servidor", async () => {
    const { loader, state, requests } = setup();
    const task = loader.load();
    requests[0].reject(new Error("Nombre privado de cliente"));
    await task;
    assert.equal(state.report, null);
    assert.equal(state.loading, false);
    assert.equal(state.error, "No fue posible cargar los indicadores. Vuelve a intentarlo.");
});

test("un error atrasado no borra una respuesta vigente", async () => {
    const { loader, state, requests } = setup();
    const first = loader.load();
    const second = loader.load();
    requests[1].resolve({ current: true });
    await second;
    requests[0].reject(new Error("error anterior"));
    await first;
    assert.equal(state.error, "");
    assert.deepEqual(state.report, { current: true });
});

test("desmontar impide publicar una respuesta tardía", async () => {
    const { loader, state, requests } = setup();
    const task = loader.load();
    loader.destroy();
    requests[0].resolve({ stale: true });
    await task;
    assert.equal(state.report, null);
});
