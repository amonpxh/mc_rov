/** @odoo-module **/

// Coordina respuestas; no calcula KPI ni mantiene datos de una empresa anterior.
export class DashboardLoader {
    constructor(state, fetchData, companyKey) {
        this.state = state;
        this.fetchData = fetchData;
        this.companyKey = companyKey;
        this.generation = 0;
        this.alive = true;
    }

    async load() {
        const generation = ++this.generation;
        const company = this.companyKey();
        this.state.report = null;
        this.state.error = "";
        this.state.loading = true;
        try {
            const report = await this.fetchData();
            if (this.alive && generation === this.generation && company === this.companyKey()) {
                this.state.report = report;
            }
        } catch {
            if (this.alive && generation === this.generation && company === this.companyKey()) {
                this.state.error = "No fue posible cargar los indicadores. Vuelve a intentarlo.";
            }
        } finally {
            if (this.alive && generation === this.generation) {
                this.state.loading = false;
            }
        }
    }

    destroy() {
        this.alive = false;
        this.generation++;
    }
}
