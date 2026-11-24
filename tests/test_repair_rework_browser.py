"""QA de Cierre con cuentas ficticias de Taller y Supervisor."""

import json

from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user

from .test_customer_commitment_browser import prepare_f3_case
from .test_repair_rework import prepare_q3_order


@tagged("post_install", "-at_install", "kpi_dashboard_browser", "repair_rework_browser")
class TestRepairReworkBrowser(HttpCase):
    """Comprueba la clasificación, el cierre pendiente y la lectura del tablero."""

    def _visit(self, path, user, script, data=None):
        self.browser_js(
            path,
            """
            (async () => {
                const until = async (read, label) => {
                    for (let n = 0; n < 250; n++) {
                        const value = read();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw Error(label);
                };
                const q = selector => document.querySelector(selector);
                const modal = selector => q('.modal ' + selector);
                const frame = () => new Promise(resolve => requestAnimationFrame(resolve));
                const showClose = async () => {
                    const tab = await until(() => [...document.querySelectorAll('.o_notebook .nav-link')]
                        .find(node => node.textContent.trim() === 'Cierre'), 'Falta la pestaña Cierre');
                    tab.click();
                };
                const data = PAYLOAD;
                CHECKS
                console.log('test successful');
            })().catch(error => console.error(error));
            """.replace(
                "PAYLOAD", json.dumps(data)
            ).replace(
                "CHECKS", script
            ),
            login=user.login,
            timeout=90,
        )

    def _classify(self, order, workshop):
        self._visit(
            f"/odoo/repair.order/{order.id}",
            workshop,
            """
            await showClose();
            const close = '[name="linea_falla_cierre_ids"]';
            const classify = close + ' button[name="action_mc_propose_rework"]';
            for (const [index, label] of ['Trabajo adicional', 'Retrabajo'].entries()) {
                const button = await until(() => document.querySelectorAll(classify)[index], 'Falta Clasificar');
                button.click();
                const kind = await until(() => modal('[name="kind"] .o_select_menu_toggler'),
                    'Falta clasificación');
                kind.click();
                const choice = await until(() =>
                    [...document.querySelectorAll('.o_field_selection_menu [data-choice-index]')]
                    .find(node => node.getClientRects().length && node.textContent.trim() === label), 'Falta ' + label);
                choice.click();
                if (index === 1) {
                    const prior = await until(() => modal('[name="previous_line_id"] input'), 'Falta trabajo anterior');
                    prior.focus();
                    prior.click();
                    prior.value = data.previous;
                    prior.dispatchEvent(new Event('input', { bubbles: true }));
                    const option = await until(() => [...document.querySelectorAll('.modal [role="option"]')]
                        .find(node => node.textContent.trim() === data.previous),
                        'Falta trabajo anterior en las opciones');
                    option.click();
                    const reason = await until(() => modal('[name="reason"] textarea'), 'Falta fundamento');
                    reason.focus();
                    reason.value = data.reason;
                    reason.dispatchEvent(new Event('input', { bubbles: true }));
                    reason.dispatchEvent(new Event('change', { bubbles: true }));
                    reason.blur();
                }
                await frame();
                modal('button[name="action_record"]').click();
                await until(() => !modal('button[name="action_record"]'), 'No se guardó la clasificación');
                await showClose();
            }
            if (q(close + ' button[name="action_mc_confirm_rework"]')) throw Error('Taller pudo ver la aprobación');
            """,
            {
                "previous": order.linea_falla_ids[0].display_name,
                "reason": "Sellado anterior falló QA Q3",
            },
        )

    def _confirm(self, order, supervisor):
        self._visit(
            f"/odoo/repair.order/{order.id}",
            supervisor,
            """
            await showClose();
            (await until(() => q('[name="linea_falla_cierre_ids"] button[name="action_mc_confirm_rework"]'),
                'Falta Revisar retrabajo tras el cierre')).click();
            await until(() => modal('[name="reason"]')?.textContent.includes(data) ||
                modal('[name="reason"] textarea')?.value === data, 'No se mostró el fundamento');
            (await until(() => modal('button[name="action_confirm"]'), 'Falta Confirmar retrabajo')).click();
            await until(() => !modal('button[name="action_confirm"]'), 'No se guardó el dictamen');
            """,
            "Sellado anterior falló QA Q3",
        )

    def test_operational_rework_in_close(self):
        company = self.env["res.company"].create({"name": "QA Operativa Q3"})
        env = self.env(context={**self.env.context, "allowed_company_ids": company.ids})
        warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
        source, _, _ = prepare_f3_case(env, warehouse, "Q3", outgoing=False)
        order = prepare_q3_order(env, source.product_id, source.lot_id)
        env["stock.quant"]._update_available_quantity(
            order.product_id,
            warehouse.lot_stock_id,
            1,
            lot_id=order.lot_id,
        )
        groups = "stock.group_stock_user,mc_rov.group_work_assignment_team"
        workshop = new_test_user(
            env, login="qa_q3_browser_workshop", company_id=company.id, lang="en_US", groups=groups
        )
        supervisor = new_test_user(
            env,
            login="qa_q3_browser_supervisor",
            company_id=company.id,
            lang="en_US",
            groups=groups + ",mc_rov.group_repair_rework_supervisor",
        )
        self._classify(order, workshop)
        env.invalidate_all()
        history = env["mc.rov.repair.rework.event"].sudo()
        proposal = history.search([("line_id", "=", order.linea_falla_ids[1].id)]).ensure_one()
        self.assertEqual((proposal.state, proposal.actor_id), ("proposal", workshop))
        extra = history.search([("line_id", "=", order.linea_falla_ids[0].id)]).ensure_one()
        self.assertEqual((extra.state, extra.actor_id), ("additional", workshop))
        order.action_repair_done()
        self.assertEqual(order.state, "done")
        kpi = env["mc.rov.repair.rework.kpi"].with_user(supervisor)
        self.assertEqual(kpi.get_summary()["pending_hours"], 2)
        self._confirm(order, supervisor)
        env.invalidate_all()
        result = history.search([("proposal_id", "=", proposal.id)]).ensure_one()
        self.assertEqual(
            (result.state, result.actor_id, result.reason), ("rework", supervisor, proposal.reason)
        )
        self.assertEqual(result.previous_line_id, order.linea_falla_ids[0])
        self.assertEqual(kpi.get_summary()["hours_percent"], 40)
        action = env.ref("mc_rov.action_kpi_dashboard")
        self._visit(
            f"/odoo/action-{action.id}",
            supervisor,
            """
            (await until(() => q('[data-section="repair_rework"]'), 'Falta sección Retrabajo')).click();
            await until(() => q('[data-kpi-repair-rework]')?.textContent.includes('2 de 5 HH'),
                'No se muestran las 2 de 5 HH');
            if (!q('[data-kpi-repair-rework]').textContent.includes('No determinado')) throw Error('Falta la causa');
            """,
        )
