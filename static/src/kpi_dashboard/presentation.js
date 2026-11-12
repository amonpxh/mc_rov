/** @odoo-module **/

// Solo presentación: los porcentajes y la población proceden del servicio autorizado.
export function formatPercent(value) {
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 100) {
        return "Sin dato";
    }
    return `${new Intl.NumberFormat("es-CL", { maximumFractionDigits: 1 }).format(value)} %`;
}

export function firstPassPresentation(row) {
    const hidden = (state, headline) => ({
        state, headline, ratio: null, population: null,
        passed: null, failed: null, pending: null, unknown: null,
        coverageRatio: null, coverageHeadline: null,
    });
    if (row?.available !== true) {
        return row?.available === false
            ? hidden("unavailable", "Sin acceso")
            : hidden("unknown", "Sin dato");
    }
    const metrics = row.metrics;
    const counts = ["population", "passed", "failed", "pending", "unknown", "evaluated"];
    if (!metrics || !counts.every((key) => Number.isInteger(metrics[key]) && metrics[key] >= 0)
        || metrics.evaluated !== metrics.passed + metrics.failed
        || metrics.population !== metrics.evaluated + metrics.pending + metrics.unknown) {
        return hidden("unknown", "Sin dato");
    }
    const state = !metrics.population ? "empty" : !metrics.evaluated ? "no_base" : "available";
    return {
        state,
        headline: metrics.evaluated ? formatPercent(metrics.value) : "Sin base",
        ratio: `${metrics.passed}/${metrics.evaluated}`,
        coverageRatio: `${metrics.evaluated}/${metrics.population}`,
        coverageHeadline: metrics.population ? formatPercent(metrics.coverage_percent) : "Sin base",
        population: metrics.population,
        passed: metrics.passed, failed: metrics.failed,
        pending: metrics.pending, unknown: metrics.unknown,
    };
}
