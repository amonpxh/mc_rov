import { Component, markup, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { AssignedWorkView } from "./assigned_work_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "@web/search/action_hook";

const SERVICE = "mc.rov.work.center";
const ASSIGNMENT = "mc.rov.work.assignment";
const AREAS = [
    { key: "repair", label: "Reparar", title: "Reparar o mantener", description: "Órdenes y revisiones de una visita.", icon: "fa-wrench" },
    { key: "manufacturing", label: "Fabricar", title: "Fabricar un equipo", description: "Órdenes, materiales y operaciones.", icon: "fa-cogs" },
    { key: "acceptance", label: "Aceptar", title: "Aceptar un equipo nuevo", description: "Configuración, RND/TRN y fichas FEN.", icon: "fa-check-square-o" },
    { key: "equipment", label: "Consultar equipo", title: "Consultar un equipo", description: "Serie, configuración e historial.", icon: "fa-search" },
    { key: "quality", label: "Calidad", title: "Gestionar Calidad", description: "Alertas, controles y lecciones.", icon: "fa-shield" },
    { key: "inventory", label: "Inventario", title: "Inventario", description: "Existencias, productos, series y operaciones.", icon: "fa-cubes" },
    { key: "design", label: "Diseño / BoM", title: "Trabajar en diseño / BoM", description: "Modelos, BoM (lista de materiales) y cambios de ingeniería.", icon: "fa-sitemap" },
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
        this.menu = useService("menu");
        this.areas = AREAS;
        const saved = this.props.state?.workCenter || {};
        this.state = useState({
            topic: saved.topic || "repair", kind: saved.kind || "orders",
            filters: saved.filters || {}, kinds: saved.kinds || {},
            overview: [], rows: [], total: 0, nextOffset: false, responsibleLabel: false,
            loading: true, error: "", overviewError: "", inventoryError: "", acting: false,
            modelQuery: "", modelOptions: [], modelError: "",
            workspace: saved.workspace || "assigned",
            assignedWork: { scope: "mine", employeeId: false, kind: "activities", process: "all", viewType: "kanban", ...saved.assignedWork },
            assignmentOpen: false, assignmentLoading: false, assignmentReady: false,
            assignmentError: "", employeeError: "", employees: [], canViewTeam: false,
            assignmentAction: null, processOptions: [], assignmentRevision: 0,
            inventory: { section: "stock", destination: "stock", viewType: false, selections: {}, viewTypes: {}, ...saved.inventory },
            inventoryDestinations: [], inventoryAction: null, inventoryLoading: false,
            inventoryCapabilitiesLoading: false, inventoryRevision: 0, inventoryCompanyKey: "",
        });
        this.inventoryGeneration = 0;
        this.inventoryCapabilitiesGeneration = 0;
        this.navigationGeneration = 0;
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
            this.inventoryGeneration++;
            this.inventoryCapabilitiesGeneration++;
            this.navigationGeneration++;
            clearTimeout(this.searchTimer);
            clearTimeout(this.modelTimer);
        });
    }

    exportState() {
        return JSON.parse(JSON.stringify({
            topic: this.state.topic, kind: this.state.kind,
            filters: this.state.filters, kinds: this.state.kinds,
            assignedWork: this.state.assignedWork, workspace: this.state.workspace,
            inventory: this.state.inventory,
        }));
    }

    get visibleAreas() {
        return this.areas.filter((area) => area.key !== "inventory"
            || this.state.overview.some((item) => item.topic === "inventory" && item.available));
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
        if (this.state.workspace === "inventory") {
            return JSON.stringify(["inventory", this.state.inventory.destination,
                this.state.inventoryCompanyKey, this.state.inventory.viewType]);
        }
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
        const view = this.nativeView;
        const key = this.nativeKey;
        if (view && !await view.canLeave()) return false;
        // Una confirmación tardía no debe guardar una vista bajo el destino nuevo.
        if (view && this.nativeView === view && this.nativeKey === key) this.nativeStates[key] = view.snapshot();
        return true;
    }
    async toggleAssignedWork() {
        const intent = ++this.navigationGeneration;
        if (!await this.leaveNativeView() || intent !== this.navigationGeneration) return;
        this.invalidateInventory();
        this.nativeView = null;
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
        const intent = ++this.navigationGeneration;
        if (!await this.leaveNativeView() || intent !== this.navigationGeneration) return;
        this.state.assignedWork.kind = "activities";
        this.state.assignedWork.process = this.state.topic;
        this.state.workspace = "assigned";
        return this.loadAssignedWork();
    }

    async refresh() {
        const intent = ++this.navigationGeneration;
        if (!await this.leaveNativeView() || intent !== this.navigationGeneration) return;
        // Reload record data while keeping the native search and grouping.
        const snapshot = this.nativeStates[this.nativeKey];
        this.nativeStates[this.nativeKey] = snapshot ? { globalState: snapshot.globalState } : {};
        if (this.state.workspace === "inventory") {
            // Retirar el puente antes de consultar capacidades evita recapturar su caché descartada.
            this.nativeView = null;
            this.state.inventoryAction = null;
            this.inventoryGeneration++;
        }
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
            if (this.state.workspace === "inventory" && this.visibleAreas.some((item) => item.key === "inventory")) {
                await this.loadInventory();
                this.state.loading = false;
            }
            else if (this.state.workspace === "assigned") {
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
        const intent = ++this.navigationGeneration;
        if (!await this.leaveNativeView() || intent !== this.navigationGeneration) return;
        if (topic === "inventory") {
            if (!this.visibleAreas.some((area) => area.key === "inventory")) return;
            if (this.state.workspace === "inventory" && this.state.inventoryCapabilitiesLoading) return;
            this.assignmentGeneration++;
            this.nativeView = null;
            this.state.workspace = "inventory";
            return this.loadInventory();
        }
        this.invalidateInventory();
        this.nativeView = null;
        this.assignmentGeneration++;
        this.state.workspace = "process";
        this.state.kinds[this.state.topic] = this.state.kind;
        this.state.topic = topic;
        this.state.kind = this.state.kinds[topic]
            || this.tabs.find((item) => item.available)?.kind || this.tabs[0]?.kind;
        this.resetModelSearch();
        this.loadRecords();
    }

    invalidateInventory() {
        this.inventoryGeneration++;
        this.inventoryCapabilitiesGeneration++;
        this.state.inventoryLoading = false;
        this.state.inventoryCapabilitiesLoading = false;
    }
    get inventorySections() {
        return [
            { key: "stock", label: "Existencias" }, { key: "products", label: "Productos" },
            { key: "lots", label: "Series y lotes" }, { key: "operations", label: "Operaciones" },
            { key: "replenishment", label: "Reabastecimiento" },
        ].map((section) => ({ ...section, available: this.state.inventoryDestinations.some(
            (entry) => entry.section === section.key && entry.available) }));
    }
    get inventoryEntries() {
        return this.state.inventoryDestinations.filter((entry) => entry.section === this.state.inventory.section);
    }
    get inventoryViews() {
        return (this.state.inventoryAction?.views || []).filter((view) =>
            ["list", "kanban", "calendar", "pivot", "graph", "activity"].includes(view[1]));
    }
    async loadInventory() {
        const generation = ++this.inventoryCapabilitiesGeneration;
        this.state.inventoryCapabilitiesLoading = true;
        this.state.inventoryError = "";
        try {
            const entries = await this.orm.call(SERVICE, "get_inventory_destinations", []);
            if (generation !== this.inventoryCapabilitiesGeneration || this.state.workspace !== "inventory") return;
            this.state.inventoryDestinations = entries;
            const work = this.state.inventory;
            const selected = entries.find((entry) => entry.key === work.destination && entry.available)
                || entries.find((entry) => entry.section === work.section && entry.available)
                || entries.find((entry) => entry.available);
            if (selected) await this.openInventoryDestination(selected.key, true);
            else this.state.inventoryAction = null;
        } catch (_error) {
            if (generation === this.inventoryCapabilitiesGeneration) {
                this.state.inventoryDestinations = [];
                this.inventoryFailed();
            }
        } finally {
            if (generation === this.inventoryCapabilitiesGeneration) this.state.inventoryCapabilitiesLoading = false;
        }
    }
    async changeInventorySection(section) {
        const choices = this.state.inventoryDestinations.filter((entry) => entry.section === section && entry.available);
        const remembered = this.state.inventory.selections[section];
        const selected = choices.find((entry) => entry.key === remembered) || choices[0];
        if (selected) return this.openInventoryDestination(selected.key);
    }
    async openInventoryDestination(key, reload = false) {
        const entry = this.state.inventoryDestinations.find((item) => item.key === key && item.available);
        if (!entry || this.state.workspace !== "inventory") return;
        const duplicate = () => this.state.inventory.destination === key
            && (this.state.inventoryLoading || (!reload && this.state.inventoryAction));
        if (duplicate()) return;
        const intent = ++this.navigationGeneration;
        if (!await this.leaveNativeView() || intent !== this.navigationGeneration
            || this.state.workspace !== "inventory" || duplicate()) return;
        const generation = ++this.inventoryGeneration;
        const work = this.state.inventory;
        work.viewTypes[work.destination] = work.viewType;
        work.section = entry.section;
        work.destination = key;
        work.selections[entry.section] = key;
        this.state.inventoryAction = null;
        this.state.inventoryLoading = true;
        this.state.inventoryError = "";
        try {
            const action = await this.orm.call(SERVICE, "action_inventory_destination", [key]);
            if (generation !== this.inventoryGeneration || this.state.workspace !== "inventory") return;
            if (typeof action.help === "string") action.help = markup(action.help);
            this.state.inventoryCompanyKey = JSON.stringify(action.context?.allowed_company_ids || []);
            this.state.inventoryAction = action;
            const preferred = work.viewTypes[key];
            work.viewType = this.inventoryViews.find((view) => view[1] === preferred)?.[1]
                || this.inventoryViews[0]?.[1] || "list";
            this.state.inventoryRevision++;
        } catch (_error) {
            if (generation === this.inventoryGeneration) this.inventoryFailed();
        } finally {
            if (generation === this.inventoryGeneration) this.state.inventoryLoading = false;
        }
    }
    inventoryFailed() {
        this.inventoryGeneration++;
        this.state.inventoryAction = null;
        this.state.inventoryLoading = false;
        this.state.inventoryError = "No se pudo abrir el destino de Inventario. Comprueba tus permisos y la conexión y vuelve a intentar.";
    }
    async retryInventory() {
        const intent = ++this.navigationGeneration;
        if (!await this.leaveNativeView() || intent !== this.navigationGeneration
            || this.state.workspace !== "inventory") return;
        if (!this.state.inventoryDestinations.length) return this.loadInventory();
        return this.openInventoryDestination(this.state.inventory.destination, true);
    }
    async changeInventoryView(type) {
        if (!this.inventoryViews.some((view) => view[1] === type)) return;
        const intent = ++this.navigationGeneration;
        if (!await this.leaveNativeView() || intent !== this.navigationGeneration
            || this.state.workspace !== "inventory") return;
        this.state.inventory.viewType = type;
        this.state.inventoryRevision++;
    }
    async openInventoryApplication() {
        if (this.state.acting || this.state.workspace !== "inventory") return;
        const intent = ++this.navigationGeneration;
        if (!await this.leaveNativeView() || intent !== this.navigationGeneration
            || this.state.workspace !== "inventory" || this.state.acting) return;
        this.state.acting = true;
        this.state.inventoryError = "";
        try {
            const { menu_id: menuId } = await this.orm.call(SERVICE, "get_inventory_application", []);
            if (intent !== this.navigationGeneration || this.state.workspace !== "inventory") return;
            const app = this.menu.getApps().find((item) => item.id === menuId);
            if (!app?.actionID) throw new Error("Aplicación no disponible en los menús autorizados");
            await this.menu.selectMenu(app);
        } catch (_error) {
            if (intent === this.navigationGeneration && this.state.workspace === "inventory") {
                this.state.inventoryError = "No se pudo abrir Inventario completo. Comprueba tus permisos y vuelve a intentar.";
            }
        } finally {
            this.state.acting = false;
        }
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

    async navigate(method, args, kwargs = {}, errorField = "error") {
        if (this.state.acting) return;
        this.state.acting = true;
        this.state[errorField] = "";
        try {
            const action = await this.orm.call(SERVICE, method, args, kwargs);
            // Odoo prepara la ayuda HTML al cargar por ID; una acción RPC evita ese paso.
            if (typeof action.help === "string") action.help = markup(action.help);
            await this.action.doAction(action);
        } catch (_error) {
            this.state[errorField] = "No se pudo abrir el destino. Comprueba que existe y que tienes acceso.";
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
