import { ArchiveDisabledListController } from "@mail/views/web/list/archive_disabled_list_controller";
import { archiveDisabledListView } from "@mail/views/web/list/archive_disabled_list_view";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";

// Keep the native activity list, scheduling dialog, search and selection model.
class AutomaticActivityListController extends ArchiveDisabledListController {
    get canCloseSelection() {
        const root = this.model.root;
        // A domain selection can contain unloaded automatic work. Do not infer
        // its identity from the visible page or grant a generic closing action.
        return !root.isDomainSelected && root.selection.length > 0 &&
            root.selection.every((record) => record.data.mc_automatic_pending === false);
    }

    evalViewModifier(modifier) {
        const context = this.model.root.evalContext;
        return evaluateBooleanExpr(modifier, {
            ...context,
            context: { ...context.context, mc_automatic_close_forbidden: !this.canCloseSelection },
        });
    }

    getStaticActionMenuItems() {
        const items = super.getStaticActionMenuItems();
        const available = items.delete.isAvailable;
        items.delete = {
            ...items.delete,
            isAvailable: () => available() && this.canCloseSelection,
        };
        return items;
    }

    onDeleteSelectedRecords(...args) {
        if (!this.activeActions.delete || !this.canCloseSelection) return;
        return super.onDeleteSelectedRecords(...args);
    }
}

registry.category("views").add("mc_automatic_activity_list", {
    ...archiveDisabledListView,
    Controller: AutomaticActivityListController,
});
