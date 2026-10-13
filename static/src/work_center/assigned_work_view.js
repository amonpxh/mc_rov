import { Component, onError, onWillUnmount, useSubEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CallbackRecorder } from "@web/search/action_hook";
import { getDefaultConfig, View } from "@web/views/view";

// Native controllers keep their search, permissions and action menus. Their
// callbacks must not write native state over the parent client action's state.
export class AssignedWorkView extends Component {
    static template = "mc_rov.AssignedWorkView";
    static components = { View };
    static props = ["action", "viewType", "saved", "register", "onError"];

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.recorders = Object.fromEntries([
            "__beforeLeave__", "__getGlobalState__", "__getLocalState__",
            "__getContext__", "__getOrderBy__",
        ].map((name) => [name, new CallbackRecorder()]));
        const action = this.props.action;
        useSubEnv({
            config: {
                ...getDefaultConfig(), actionId: action.id || false,
                actionType: "ir.actions.act_window", actionXmlId: action.xml_id || false,
                views: action.views, viewSwitcherEntries: [], breadcrumbs: [],
            },
        });
        onError(() => this.props.onError());
        this.props.register(this);
        onWillUnmount(() => this.props.register(null, this));
    }
    collect(name) {
        return Object.assign({}, ...this.recorders[name].callbacks.map((callback) => callback()));
    }
    snapshot() {
        return { globalState: this.collect("__getGlobalState__"), state: this.collect("__getLocalState__") };
    }
    async canLeave() {
        for (const callback of this.recorders.__beforeLeave__.callbacks) {
            if (await callback() === false) return false;
        }
        return true;
    }
    get viewProps() {
        const action = this.props.action;
        return {
            resModel: action.res_model, type: this.props.viewType,
            views: action.views, domain: action.domain || [], context: action.context || {},
            searchViewId: Array.isArray(action.search_view_id) ? action.search_view_id[0] : action.search_view_id || false,
            loadActionMenus: true, loadIrFilters: true, noBreadcrumbs: true,
            display: { controlPanel: { breadcrumbs: false, viewSwitcher: false }, searchPanel: true },
            noContentHelp: action.help,
            globalState: this.props.saved.globalState, state: this.props.saved.state,
            ...this.recorders,
            selectRecord: (id, options) => this.openRecord(id, options),
            createRecord: () => this.openRecord(false),
        };
    }
    async openRecord(id, options = {}) {
        let action;
        if (id && this.props.action.res_model === "mail.activity") {
            action = await this.orm.call("mc.rov.work.assignment", "action_open_source", [id]);
        } else {
            action = { type: "ir.actions.act_window", res_model: this.props.action.res_model,
                res_id: id || false, views: [[false, "form"]],
                context: { ...this.props.action.context }, };
        }
        return this.actionService.doAction(action, { newWindow: options.newWindow });
    }
}
