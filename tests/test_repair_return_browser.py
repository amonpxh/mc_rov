"""QA operativo de Q2 con Taller, Supervisor y un navegador real."""

import json

from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user

from .test_repair_returns import prepare_q2_case


@tagged("post_install", "-at_install", "kpi_dashboard_browser", "repair_return_browser")
class TestRepairReturnBrowser(HttpCase):
    """Vincula dos retornos y comprueba ambos dictámenes y sus conteos."""

    def _visit(self, path, login, script, data=None):
        self.browser_js(
            path,
            """
            (async () => {
                const until = async (read, label) => {
                    for (let attempt = 0; attempt < 250; attempt++) {
                        const value = read();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw Error(label);
                };
                const q = selector => document.querySelector(selector);
                const modal = selector => q('.modal ' + selector);
                const frame = () => new Promise(resolve => requestAnimationFrame(resolve));
                const data = PAYLOAD;
                CHECKS
                console.log('test successful');
            })().catch(error => console.error(error));
            """.replace(
                "PAYLOAD", json.dumps(data)
            ).replace(
                "CHECKS", script
            ),
            login=login,
            timeout=80,
        )

    def _link(self, original, returned, workshop):
        self._visit(
            f"/odoo/repair.order/{returned.id}",
            workshop.login,
            """
            const button = await until(() => q('button[name="action_mc_link_return"]'),
                'Falta Vincular retorno');
            if (q('button[name="action_mc_decide_return"]')) throw Error('Taller puede dictaminar');
            button.click();
            const input = await until(() => modal('[name="original_id"] input'),
                'Falta selector de reparación anterior');
            input.focus();
            input.click();
            input.value = data;
            input.dispatchEvent(new Event('input', { bubbles: true }));
            const option = await until(() => [...document.querySelectorAll('.modal [role="option"]')]
                .find(node => node.textContent.trim() === data), 'La visita original no aparece');
            option.click();
            await frame();
            modal('button[name="action_link"]').click();
            await until(() => !modal('button[name="action_link"]'), 'El vínculo no se guardó');
            """,
            original.display_name,
        )
        self.env.invalidate_all()
        entry = (
            self.env["mc.rov.repair.return"]
            .sudo()
            .search([("return_id", "=", returned.id)])
            .ensure_one()
        )
        self.assertEqual(
            (entry.original_id, entry.linked_by, entry.relation), (original, workshop, "pending")
        )
        return entry

    def _decide(self, returned, entry, supervisor, verdict):
        relation, label, reason = verdict
        self._visit(
            f"/odoo/repair.order/{returned.id}",
            supervisor.login,
            """
            const button = await until(() => q('button[name="action_mc_decide_return"]'),
                'Falta Dictaminar retorno');
            button.click();
            const select = await until(() => modal('[name="relation"] .o_select_menu_toggler'),
                'Falta selector de dictamen');
            select.click();
            const option = await until(() =>
                [...document.querySelectorAll('.o_field_selection_menu [data-choice-index]')]
                    .find(item => item.getClientRects().length && item.textContent.trim() === data.label),
                'No está disponible el dictamen ' + data.label);
            option.click();
            await frame();
            const reason = await until(() => modal('[name="reason"] textarea'), 'Falta fundamento');
            reason.focus();
            reason.value = data.reason;
            reason.dispatchEvent(new Event('input', { bubbles: true }));
            reason.dispatchEvent(new Event('change', { bubbles: true }));
            reason.blur();
            await frame();
            modal('button[name="action_decide"]').click();
            await until(() => !modal('button[name="action_decide"]'), 'No se guardó el dictamen');
            """,
            {"label": label, "reason": reason},
        )
        self.env.invalidate_all()
        self.assertEqual(
            (entry.relation, entry.decided_by, entry.reason), (relation, supervisor, reason)
        )
        self.assertTrue(entry.decided_at)

    def test_operational_link_and_both_verdicts(self):
        company = self.env["res.company"].create({"name": "QA Operativa Q2"})
        env = self.env(context={**self.env.context, "allowed_company_ids": company.ids})
        warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
        groups = "stock.group_stock_user,mc_rov.group_work_assignment_team"
        workshop = new_test_user(
            env,
            login="qa_q2_browser_taller",
            company_id=company.id,
            lang="en_US",
            groups=groups,
        )
        supervisor = new_test_user(
            env,
            login="qa_q2_browser_supervisor",
            company_id=company.id,
            lang="en_US",
            groups=groups
            + ",mc_rov.group_repair_return_supervisor,mc_rov.group_customer_commitment_supervisor",
        )
        for verdict in (
            ("confirmed", "Relacionada con la reparación", "Falla de la reparación anterior QA"),
            ("unrelated", "Otra causa", "Daño posterior documentado QA"),
        ):
            original, returned = prepare_q2_case(env, warehouse, verdict[0], workshop, supervisor)
            entry = self._link(original, returned, workshop)
            self._decide(returned, entry, supervisor, verdict)
            self.assertEqual((entry.original_id, entry.linked_by), (original, workshop))
        action = env.ref("mc_rov.action_kpi_dashboard")
        self._visit(
            f"/odoo/action-{action.id}",
            supervisor.login,
            """
            const section = await until(() => q('[data-section="repair_returns"]'), 'Falta Retornos');
            section.click();
            const board = await until(() => q('[data-kpi-repair-returns]'), 'Falta tablero Q2');
            await until(() => [...board.querySelectorAll('.mc_kpi_value')]
                .map(node => node.textContent.trim()).join(',') === '2,1,0,1',
                'Los conteos deben mostrar dos retornos, uno relacionado y otro por otra causa');
            if (!board.textContent.includes('Tasa pendiente de seguimiento acreditado')) {
                throw Error('El tablero no identificó la cobertura pendiente');
            }
            """,
        )
