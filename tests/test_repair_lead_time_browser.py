"""Ensayo operativo de las dos modalidades de recepción F6."""

from datetime import timedelta
import json

from odoo import fields
from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user

from ..models.production_kpi_metrics import local_day
from .test_customer_commitment_browser import dispatch_wizard, prepare_f3_case
from .test_repair_lead_time import receive_rov


@tagged("post_install", "-at_install", "kpi_dashboard_browser", "repair_lead_time_browser")
class TestRepairLeadTimeBrowser(HttpCase):
    """Registra ambas llegadas desde el formulario y contrasta el tablero con el historial."""

    def _record_arrival(self, visit, operator, delayed_at=None):
        self.browser_js(
            f"/odoo/repair.order/{visit.id}",
            """
            (async () => {
                const until = async (read, label) => {
                    for (let attempt = 0; attempt < 250; attempt++) {
                        const value = read();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw new Error(label);
                };
                const delayed = ARRIVAL;
                const modal = selector => document.querySelector('.modal ' + selector);
                const arrival = await until(() => document.querySelector(
                    'button[name="action_mc_record_arrival"]'), 'Falta el botón de llegada');
                arrival.click();
                const toggle = await until(() => modal('[name="delayed"] input'),
                    'Falta la opción de validación posterior');
                if (modal('[name="arrived_at"] input')?.getClientRects().length) {
                    throw new Error('La fecha manual debe empezar oculta');
                }
                if (delayed) {
                    toggle.click();
                    const dateInput = await until(() => modal('[name="arrived_at"] input'),
                        'Falta la fecha efectiva');
                    const reason = await until(() => modal('[name="reason"] textarea'),
                        'Falta el motivo');
                    dateInput.focus();
                    dateInput.value = delayed;
                    dateInput.dispatchEvent(new Event('input', { bubbles: true }));
                    dateInput.dispatchEvent(new Event('change', { bubbles: true }));
                    reason.focus();
                    reason.value = 'La recepción se validó después QA F6';
                    reason.dispatchEvent(new Event('input', { bubbles: true }));
                    reason.dispatchEvent(new Event('change', { bubbles: true }));
                    reason.blur();
                }
                modal('button[name="action_apply"]').click();
                await until(() => !modal('button[name="action_apply"]'),
                    'El asistente no guardó la llegada');
                console.log('test successful');
            })().catch(error => console.error(error));
            """.replace(
                "ARRIVAL", json.dumps(delayed_at)
            ),
            login=operator.login,
            timeout=75,
        )

    def _case(self, label):
        company = self.env["res.company"].create({"name": f"QA F6 {label}"})
        env = self.env(context={**self.env.context, "allowed_company_ids": company.ids})
        warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
        repair, outgoing, attachment = prepare_f3_case(env, warehouse, label)
        receipt = receive_rov(env, warehouse, repair)
        repair.picking_id = receipt
        operator = new_test_user(
            env,
            login=f"qa_f6_{label}",
            company_id=company.id,
            lang="en_US",
            tz="UTC",
            groups="stock.group_stock_manager,mc_rov.group_work_assignment_team,"
            "mc_rov.group_customer_commitment_supervisor",
        )
        return repair.with_user(operator), receipt, outgoing.with_user(operator), attachment

    def _assert_arrival(self, repair, receipt, actual, reason=False):
        evidence = (
            repair.env["mc.rov.repair.arrival"]
            .sudo()
            .search([("repair_id", "=", repair.id)])
            .ensure_one()
        )
        self.assertEqual(evidence.actor_id, repair.env.user)
        self.assertEqual(evidence.picking_id, receipt)
        self.assertEqual(evidence.lot_id, repair.lot_id)
        self.assertEqual(evidence.arrived_at, actual)
        self.assertEqual(evidence.validated_at, receipt.date_done)
        self.assertEqual(evidence.reason, reason)

    def test_receipt_validated_on_arrival(self):
        repair, receipt, _outgoing, _attachment = self._case("onsite")
        self._record_arrival(repair, repair.env.user)
        self._assert_arrival(repair, receipt, receipt.date_done)

    def test_delayed_validation_and_dashboard(self):
        repair, receipt, outgoing, attachment = self._case("delayed")
        actual = (receipt.date_done - timedelta(days=3)).replace(second=0)
        self._record_arrival(repair, repair.env.user, actual.strftime("%m/%d/%Y %H:%M:%S"))
        self._assert_arrival(repair, receipt, actual, "La recepción se validó después QA F6")
        now = fields.Datetime.now()
        dispatch_wizard(outgoing, repair, attachment, now).action_apply()
        expected = (local_day(now) - local_day(actual)).days
        summary = repair.env["mc.rov.repair.lead.time.kpi"].get_summary()
        self.assertEqual((summary["samples"], summary["median_days"]), (1, expected))
        action = self.env.ref("mc_rov.action_kpi_dashboard")
        self.browser_js(
            f"/odoo/action-{action.id}",
            """
            (async () => {
                for (let n = 0; n < 200; n++) {
                    const button = document.querySelector('[data-section="repair_lead_time"]');
                    const board = document.querySelector('[data-kpi-repair-lead-time]');
                    if (!board && button && button.getAttribute('aria-selected') === 'false') button.click();
                    if (board?.textContent.includes('1 de 1') &&
                        board.querySelector('.mc_kpi_value')?.textContent.trim() === 'EXPECTED') {
                        console.log('test successful');
                        return;
                    }
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
                throw Error('F6 no mostró la mediana de la llegada efectiva');
            })().catch(error => console.error(error));
            """.replace(
                "EXPECTED", str(expected)
            ),
            login=repair.env.user.login,
            timeout=65,
        )
