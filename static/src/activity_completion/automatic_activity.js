// The native model methods must exist before adding these pending-work guards.
import "@mail/core/web/activity_model_patch";
import { Activity as ActivityRecord } from "@mail/core/common/activity_model";
import { fields } from "@mail/core/common/record";
import { Activity } from "@mail/core/web/activity";
import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";
import { ActivityMarkAsDone } from "@mail/core/web/activity_markasdone_popover";
import { ActivityCalendarCommonPopover } from "@mail/views/web/calendar/calendar_common/activity_calendar_common_popover";
import { patch } from "@web/core/utils/patch";

async function openOperation(component) {
    const action = await component.env.services.orm.call(
        "mail.activity", "action_open_document", [[component.props.activity.id]]
    );
    return component.env.services.action.doAction(action);
}

patch(ActivityRecord.prototype, {
    setup() {
        super.setup(...arguments);
        this.mc_automatic_pending = fields.Attr(false);
    },
    async markAsDone(...args) {
        if (this.mc_automatic_pending) return;
        return super.markAsDone(...args);
    },
    async markAsDoneAndScheduleNext(...args) {
        if (this.mc_automatic_pending) return;
        return super.markAsDoneAndScheduleNext(...args);
    },
});

patch(Activity.prototype, {
    mcOpenOperation() {
        return openOperation(this);
    },
    async onClickMarkAsDone(...args) {
        if (this.props.activity.mc_automatic_pending) return;
        return super.onClickMarkAsDone(...args);
    },
    async onFileUploaded(...args) {
        if (this.props.activity.mc_automatic_pending) return;
        return super.onFileUploaded(...args);
    },
    async unlink() {
        if (this.props.activity.mc_automatic_pending) return;
        const thread = this.thread;
        // Even a stale client must not hide a record before the server accepts
        // cancellation. A rejected RPC leaves the pending activity visible.
        await this.env.services.orm.unlink("mail.activity", [this.props.activity.id]);
        this.props.activity.remove();
        this.props.onActivityChanged(thread);
    },
});

patch(ActivityListPopoverItem.prototype, {
    get hasMarkDoneButton() {
        return !this.props.activity.mc_automatic_pending && super.hasMarkDoneButton;
    },
    get hasCancelButton() {
        return !this.props.activity.mc_automatic_pending && super.hasCancelButton;
    },
    get hasFileUploader() {
        return !this.props.activity.mc_automatic_pending && super.hasFileUploader;
    },
    mcOpenOperation() {
        return openOperation(this);
    },
    onClickMarkAsDone(...args) {
        if (this.props.activity.mc_automatic_pending) return;
        return super.onClickMarkAsDone(...args);
    },
    async onFileUploaded(...args) {
        if (this.props.activity.mc_automatic_pending) return;
        return super.onFileUploaded(...args);
    },
    async unlink() {
        if (this.props.activity.mc_automatic_pending) return;
        await this.env.services.orm.unlink("mail.activity", [this.props.activity.id]);
        this.props.activity.remove();
        this.props.onActivityChanged?.();
    },
});

patch(ActivityMarkAsDone.prototype, {
    async onClickDone(...args) {
        if (this.props.activity.mc_automatic_pending) return;
        return super.onClickDone(...args);
    },
    async onClickDoneAndScheduleNext(...args) {
        if (this.props.activity.mc_automatic_pending) return;
        return super.onClickDoneAndScheduleNext(...args);
    },
});

// The native yearly calendar already opens the source by clicking its event.
// Day/week/month use a reference in the popover body, including mobile dialogs.
patch(ActivityCalendarCommonPopover, {
    subTemplates: {
        ...ActivityCalendarCommonPopover.subTemplates,
        body: "mc_rov.AutomaticActivityCalendarBody",
    },
});
patch(ActivityCalendarCommonPopover.prototype, {
    onDeleteEvent(...args) {
        if (this.props.record.rawRecord.mc_automatic_pending) return;
        return super.onDeleteEvent(...args);
    },
});
