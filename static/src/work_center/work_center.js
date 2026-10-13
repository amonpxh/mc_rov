import { Component, markup, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { AssignedWorkView } from "./assigned_work_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "@web/search/action_hook";

const SERVICE = "mc.rov.work.center";
const ASSIGNMENT = "mc.rov.work.assignment";
const AREAS = [
    { key: "repair", title: "Reparar o mantener", description: "Órdenes y revisiones de una visita.", icon: "fa-wrench" },
    { key: "manufacturing", title: "Fabricar un equipo", description: "Órdenes, materiales y operaciones.", icon: "fa-cogs" },
    { key: "acceptance", title: "Aceptar un equipo nuevo", description: "Configuración, RND/TRN y fichas FEN.", icon: "fa-check-square-o" },
    { key: "equipment", title: "Consultar un equipo", description: "Serie, configuración e historial.", icon: "fa-search" },
    { key: "quality", title: "Gestionar Calidad", description: "Alertas, controles y lecciones.", icon: "fa-shield" },
    { key: "design", title: "Trabajar en diseño / BoM", description: "Modelos, BoM (lista de materiales) y cambios de ingeniería.", icon: "fa-cubes" },
];
const KINDS = {
    orders: ["Órdenes", "Nueva orden", "Ver todas las órdenes"],
    reviews: ["Revisiones", "Nueva revisión", "Ver todas las revisiones"],
    manufacturing: ["Fabricaciones", "Nueva fabricación", "Ver todas las fabricaciones"],
    equipment: ["Equipos", "Nuevo equipo", "Ver todos los equipos"],
    performance: ["Rendimiento", "Elegir equipo para RND", "Ver todas las pruebas de rendimiento"],
    field: ["Terreno", "Elegir equipo para TRN", "Ver todas las pruebas de terreno"],
    fen: ["Fichas", "Elegir equipo para FEN", "Ver todas las fichas"],
    alerts: ["Alertas", "Nueva alerta", "Ver todas las alertas"],
    checks: ["Controles", "", "Ver todos los controles"],
    lessons: ["Lecciones", "", "Ver todas las lecciones"],
    models: ["Modelos", "Nuevo modelo", "Ver todos los modelos"],
    bom: ["BoM", "Nueva BoM", "Ver todas las BoM"],
    changes: ["Cambios", "Nuevo cambio", "Ver todos los cambios"],
};

export class WorkCenter extends Component {
    static template = "mc_rov.WorkCenter";
    static props = ["*"];
    static components = { AssignedWorkView };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.areas = AREAS;
        const saved = this.props.state?.workCenter || {};
        this.state = useState({
            topic: saved.topic || "repair", kind: saved.kind || "orders",
            filters: saved.filters || {}, kinds: saved.kinds || {},
            overview: [], rows: [], total: 0, nextOffset: false, responsibleLabel: false,
            loading: true, error: "", overviewError: "", acting: false,
            modelQuery: "", modelOptions: [], modelError: "",
            workspace: saved.workspace || "assigned",
            assignedWork: { scope: "mine", employeeId: false, kind: "activities", process: "all", viewType: "kanban", ...saved.assignedWork },
            assignmentOpen: false, assignmentLoading: false, assignmentReady: false,
            assignmentError: "", employeeError: "", employees: [], canViewTeam: false,
            assignmentAction: null, processOptions: [], assignmentRevision: 0,
        });
        this.assignmentGeneration = 0;
        this.nativeStates = this.props.state?.assignedNativeStates || {};
        this.nativeView = null;
        this.generation = 0;
        this.modelGeneration = 0;
        useSetupAction({
            beforeLeave: () => this.leaveNativeView(),
            getLocalState: () => {
                this.captureNativeView();
                return { workCenter: this.exportState(), assignedNativeStates: this.nativeStates };
            },
        });
        onWillStart(() => this.initialize());
        onWillUnmount(() => {
            this.generation++;
            this.assignmentGeneration++;
            this.modelGeneration++;
            clearTimeout(this.searchTimer);
            clearTimeout(this.modelTimer);
        });
    }

    exportState() {
        return JSON.parse(JSON.stringify({
            topic: this.state.topic, kind: this.state.kind,
            filters: this.state.filters, kinds: this.state.kinds,
            assignedWork: this.state.assignedWork, workspace: this.state.workspace,
        }));
    }

    get area() { return AREAS.find((area) => area.key === this.state.topic); }
    get tabs() { return this.state.overview.filter((item) => item.topic === this.state.topic); }
    get capability() { return this.tabs.find((item) => item.kind === this.state.kind); }
    get labels() { return KINDS[this.state.kind] || ["Registros", "", "Ver registros"]; }
    get filter() {
        const key = `${this.state.topic}:${this.state.kind}`;
        if (!this.state.filters[key]) {
            this.state.filters[key] = { query: "", model_id: false, state_filter: this.state.kind === "equipment" ? "all" : "open", offset: 0 };
        }
        if (this.state.kind === "equipment" && this.state.filters[key].state_filter === "open") {
            this.state.filters[key].state_filter = "all";
        }
        return this.state.filters[key];
    }
    get usesState() { return !["models", "bom", "lessons"].includes(this.state.kind); }
    tabLabel(kind) { return KINDS[kind]?.[0] || kind; }

    assignmentFailed() {
        this.assignmentGeneration++;
        this.state.assignmentAction = null;
        this.state.assignmentReady = false;
        this.state.assignmentLoading = false;
        this.state.assignmentError = "No se pudo cargar la vista nativa. Comprueba la conexión y vuelve a intentar.";
    }
    get assignmentViews() {
        return (this.state.assignmentAction?.views || []).filter((view) =>
            ["list", "kanban", "calendar"].includes(view[1]));
    }
    get nativeKey() {
        const work = this.state.assignedWork;
        return JSON.stringify([work.kind, work.scope, work.kind === "activities" ? work.employeeId : false,
            work.process, work.viewType]);
    }
    get nativeState() { return this.nativeStates[this.nativeKey] || {}; }
    registerNativeView(view, previous) {
        if (view || this.nativeView === previous) this.nativeView = view;
    }
    captureNativeView() {
        if (this.nativeView) this.nativeStates[this.nativeKey] = this.nativeView.snapshot();
    }
    async leaveNativeView() {
        if (this.nativeView && !await this.nativeView.canLeave()) return false;
        this.captureNativeView();
        return true;
    }
    async toggleAssignedWork() {
        if (!await this.leaveNativeView()) return;
        this.state.workspace = "assigned";
        return this.loadAssignedWork();
    }
    async loadAssignedWork() {
        const generation = ++this.assignmentGeneration;
        this.state.assignmentLoading = true;
        this.state.assignmentReady = false;
        this.state.assignmentAction = null;
        this.state.assignmentError = "";
        try {
            const capabilities = await this.orm.call(ASSIGNMENT, "get_capabilities", []);
            if (generation !== this.assignmentGeneration) return;
            this.state.canViewTeam = capabilities.can_view_team;
            if (!capabilities.can_view_team || !["mine", "team"].includes(this.state.assignedWork.scope)) {
                this.state.assignedWork.scope = "mine";
            }
            try {
                this.state.employees = await this.orm.searchRead("hr.employee.public",
                    [["active", "=", true]], ["display_name"], { order: "name" });
                if (generation !== this.assignmentGeneration) return;
                this.state.employeeError = "";
                if (!this.state.employees.some((employee) => employee.id === this.state.assignedWork.employeeId)) {
                    this.state.assignedWork.employeeId = false;
                }
            } catch (_error) {
                if (generation !== this.assignmentGeneration) return;
                this.state.employees = [];
                this.state.assignedWork.employeeId = false;
                this.state.employeeError = "No se pudo consultar el filtro de empleados.";
            }
            const work = this.state.assignedWork;
            const options = await this.orm.call(ASSIGNMENT, "get_processes", [], { kind: work.kind });
            if (generation !== this.assignmentGeneration) return;
            this.state.processOptions = options;
            if (!options.some((option) => option.key === work.process && option.available)) work.process = "all";
            const kwargs = { scope: work.scope, process: work.process };
            if (work.kind === "activities") kwargs.employee_id = work.employeeId || false;
            const action = await this.orm.call(ASSIGNMENT, `action_${work.kind}`, [], kwargs);
            if (generation !== this.assignmentGeneration) return;
            if (typeof action.help === "string") action.help = markup(action.help);
            this.state.assignmentAction = action;
            if (!this.assignmentViews.some((view) => view[1] === work.viewType)) {
                work.viewType = this.assignmentViews.find((view) => view[1] === "kanban")?.[1]
                    || this.assignmentViews[0]?.[1] || "list";
            }
            this.state.assignmentRevision++;
            this.state.assignmentReady = true;
        } catch (_error) {
            if (generation === this.assignmentGeneration) {
                this.state.assignmentError = "No se pudo consultar el trabajo asignado. Comprueba tus permisos y vuelve a intentar.";
            }
        } finally {
            if (generation === this.assignmentGeneration) this.state.assignmentLoading = false;
        }
    }
    changeAssignedEmployee(event) {
        return this.changeAssignedWork("employeeId", Number(event.target.value) || false);
    }
    async changeAssignedWork(field, value) {
        if (!await this.leaveNativeView()) { this.render(); return; }
        this.state.assignedWork[field] = value;
        if (field === "kind") this.state.assignedWork.process = "all";
        return this.loadAssignedWork();
    }
    async changeAssignedView(type) {
        if (!await this.leaveNativeView()) return;
        this.state.assignedWork.viewType = type;
        this.state.assignmentRevision++;
    }
    async assignedForProcess() {
        if (!await this.leaveNativeView()) return;
        this.state.assignedWork.kind = "activities";
        this.state.assignedWork.process = this.state.topic;
        this.state.workspace = "assigned";
        return this.loadAssignedWork();
    }

    async refresh() {
        if (!await this.leaveNativeView()) return;
        // Reload record data while keeping the native search and grouping.
        const snapshot = this.nativeStates[this.nativeKey];
        this.nativeStates[this.nativeKey] = snapshot ? { globalState: snapshot.globalState } : {};
        return this.initialize();
    }
    async initialize() {
        this.state.loading = true;
        try {
            this.state.overview = await this.orm.call(SERVICE, "get_overview", []);
            this.state.overviewError = "";
            if (!this.capability) {
                const first = this.tabs.find((item) => item.available);
                this.state.kind = first?.kind || this.tabs[0]?.kind || "orders";
            }
            if (this.state.workspace === "assigned") {
                await this.loadAssignedWork();
                this.state.loading = false;
            }
            else await this.loadRecords();
        } catch (_error) {
            this.state.overviewError = "No se pudo cargar el centro. Comprueba la conexión y vuelve a intentar.";
            this.state.loading = false;
        }
    }

    async selectTopic(topic) {
        if (!await this.leaveNativeView()) return;
        this.assignmentGeneration++;
        this.state.workspace = "process";
        this.state.kinds[this.state.topic] = this.state.kind;
        this.state.topic = topic;
        this.state.kind = this.state.kinds[topic]
            || this.tabs.find((item) => item.available)?.kind || this.tabs[0]?.kind;
        this.resetModelSearch();
        this.loadRecords();
    }

    selectKind(kind) {
        this.state.kind = kind;
        this.resetModelSearch();
        this.loadRecords();
    }

    async loadRecords() {
        clearTimeout(this.searchTimer);
        const generation = ++this.generation;
        this.state.rows = [];
        this.state.responsibleLabel = false;
        this.state.error = "";
        this.state.loading = true;
        if (!this.capability?.available) {
            this.state.loading = false;
            this.state.total = 0;
            return;
        }
        const { query, model_id, state_filter, offset } = this.filter;
        try {
            const result = await this.orm.call(SERVICE, "get_records",
                [this.state.topic, this.state.kind], { query, model_id, state_filter, offset });
            if (generation !== this.generation) return;
            this.state.rows = result.rows;
            this.state.responsibleLabel = result.responsible_label || false;
            this.state.total = result.total;
            this.state.nextOffset = result.next_offset;
        } catch (_error) {
            if (generation !== this.generation) return;
            this.state.error = "No se pudieron consultar los registros. El acceso puede haber cambiado; vuelve a intentar.";
        } finally {
            if (generation === this.generation) this.state.loading = false;
        }
    }

    search(event) {
        this.filter.query = event.target.value;
        this.filter.offset = 0;
        this.generation++;
        this.state.rows = [];
        this.state.loading = true;
        clearTimeout(this.searchTimer);
        this.searchTimer = setTimeout(() => this.loadRecords(), 250);
    }

    changeState(event) {
        this.filter.state_filter = event.target.value;
        this.filter.offset = 0;
        this.loadRecords();
    }

    page(offset) {
        this.filter.offset = offset;
        this.loadRecords();
    }

    resetModelSearch() {
        this.modelGeneration++;
        clearTimeout(this.modelTimer);
        this.state.modelQuery = "";
        this.state.modelOptions = [];
        this.state.modelError = "";
    }

    searchModel(event) {
        this.state.modelQuery = event.target.value;
        const generation = ++this.modelGeneration;
        clearTimeout(this.modelTimer);
        this.state.modelOptions = [];
        if (!this.state.modelQuery.trim()) return;
        this.modelTimer = setTimeout(async () => {
            try {
                const result = await this.orm.call(SERVICE, "get_equipment_models", [],
                    { query: this.state.modelQuery });
                if (generation === this.modelGeneration) {
                    this.state.modelOptions = result.rows;
                    this.state.modelError = result.total ? "" : "No se encontraron modelos.";
                }
            } catch (_error) {
                if (generation === this.modelGeneration) this.state.modelError = "No se pudieron consultar modelos.";
            }
        }, 250);
    }

    chooseModel(model) {
        this.filter.model_id = model ? model.id : false;
        this.filter.model_label = model ? model.reference : "";
        this.filter.offset = 0;
        this.resetModelSearch();
        this.loadRecords();
    }

    async navigate(method, args, kwargs = {}) {
        if (this.state.acting) return;
        this.state.acting = true;
        this.state.error = "";
        try {
            const action = await this.orm.call(SERVICE, method, args, kwargs);
            // Odoo prepara la ayuda HTML al cargar por ID; una acción RPC evita ese paso.
            if (typeof action.help === "string") action.help = markup(action.help);
            await this.action.doAction(action);
        } catch (_error) {
            this.state.error = "No se pudo abrir el destino. Comprueba que existe y que tienes acceso.";
        } finally {
            this.state.acting = false;
        }
    }

    open(record) { return this.navigate("action_open", [this.state.topic, this.state.kind, record.id]); }
    create() { return this.navigate("action_create", [this.state.topic, this.state.kind]); }
    openCandidates() { return this.navigate("action_candidates", []); }
    openList() {
        const { query, model_id, state_filter } = this.filter;
        return this.navigate("action_list", [this.state.topic, this.state.kind], { query, model_id, state_filter });
    }
}

registry.category("actions").add("mc_rov.work_center", WorkCenter);
