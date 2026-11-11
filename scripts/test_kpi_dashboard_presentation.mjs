import assert from "node:assert/strict";
import test from "node:test";

let presentation = null;
try {
    presentation = await import("../static/src/kpi_dashboard/presentation.js");
} catch (error) {
    if (error.code !== "ERR_MODULE_NOT_FOUND") throw error;
}

function view(row) {
    assert.ok(presentation, "Falta la presentación del tablero");
    return presentation.firstPassPresentation(row);
}

const metrics = (overrides = {}) => ({
    population: 4, passed: 2, failed: 1, pending: 1, unknown: 0,
    evaluated: 3, value: 200 / 3, coverage_percent: 75, ...overrides,
});

test("sin acceso no muestra los conteos recibidos", () => {
    const result = view({ available: false, metrics: metrics() });
    assert.equal(result.state, "unavailable");
    assert.equal(result.headline, "Sin acceso");
    assert.equal(result.population, null);
    assert.equal(result.ratio, null);
    assert.equal(result.coverageRatio, null);
});

test("porcentaje y n/N conservan la población consultada", () => {
    const result = view({ available: true, metrics: metrics() });
    assert.equal(result.headline, "66,7 %");
    assert.equal(result.ratio, "2/3");
    assert.equal(result.population, 4);
    assert.equal(result.pending, 1);
});

test("cero por ciento evaluado es un dato válido", () => {
    const result = view({ available: true, metrics: metrics({ population: 2, passed: 0, failed: 2, pending: 0, evaluated: 2, value: 0, coverage_percent: 100 }) });
    assert.equal(result.headline, "0 %");
    assert.equal(result.ratio, "0/2");
});

test("sin evaluados no se convierte en cero por ciento", () => {
    const result = view({ available: true, metrics: metrics({ population: 2, passed: 0, failed: 0, pending: 1, unknown: 1, evaluated: 0, value: null, coverage_percent: 0 }) });
    assert.equal(result.state, "no_base");
    assert.equal(result.headline, "Sin base");
    assert.equal(result.unknown, 1);
});

test("selección vacía se distingue de pendiente y desconocida", () => {
    const result = view({ available: true, metrics: metrics({ population: 0, passed: 0, failed: 0, pending: 0, unknown: 0, evaluated: 0, value: null, coverage_percent: null }) });
    assert.equal(result.state, "empty");
    assert.equal(result.headline, "Sin base");
    assert.equal(result.population, 0);
    assert.equal(result.coverageHeadline, "Sin base");
});

test("respuesta inconsistente no aparenta un resultado fiable", () => {
    const result = view({ available: true, metrics: metrics({ evaluated: 1 }) });
    assert.equal(result.state, "unknown");
    assert.equal(result.headline, "Sin dato");
});

test("denominador positivo sin porcentaje permanece desconocido", () => {
    const result = view({ available: true, metrics: metrics({ value: null }) });
    assert.equal(result.headline, "Sin dato");
    assert.equal(result.ratio, "2/3");
});

test("aprobación alta no oculta cobertura baja de la selección", () => {
    const result = view({ available: true, metrics: metrics({ population: 100, passed: 1, failed: 0, pending: 0, unknown: 99, evaluated: 1, value: 100, coverage_percent: 1 }) });
    assert.equal(result.headline, "100 %");
    assert.equal(result.ratio, "1/1");
    assert.equal(result.coverageRatio, "1/100");
    assert.equal(result.coverageHeadline, "1 %");
});
