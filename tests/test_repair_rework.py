"""Q3 conserva la frontera entre propuestas y retrabajos confirmados."""

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .acceptance_activity_common import AcceptanceActivityCommon


@tagged("post_install", "-at_install", "repair_rework")
class TestRepairRework(AcceptanceActivityCommon):
    """Prueba el flujo desde las líneas del cierre nativo de Reparación."""

    def _case(self):
        order = self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "product_qty": 1,
                "product_uom": self.product.uom_id.id,
                "lot_id": self.lot.id,
                "company_id": self.env.company.id,
                "tipo_intervencion_ids": [
                    Command.set(self.env.ref("mc_rov.tipo_reparacion_correctiva").ids)
                ],
                "linea_falla_ids": [
                    Command.create(
                        {
                            "componente_id": self.env.ref("mc_rov.comp_motor").id,
                            "accion_id": self.env.ref("mc_rov.accion_reparacion").id,
                            "origen": "desconocida",
                            "horas": hours,
                        }
                    )
                    for hours in (3, 2)
                ],
            }
        )
        groups = "stock.group_stock_user,mc_rov.group_work_assignment_team"
        operator = new_test_user(self.env, login="qa_q3_workshop", groups=groups)
        supervisor = new_test_user(
            self.env,
            login="qa_q3_supervisor",
            groups=groups + ",mc_rov.group_repair_rework_supervisor",
        )
        return order, operator, supervisor

    def _wizard(self, line, *, review=False, **values):
        action = line.action_mc_confirm_rework() if review else line.action_mc_propose_rework()
        return line.env[action["res_model"]].with_context(**action["context"]).create(values)

    def _propose(self, lines, operator):
        self._wizard(
            lines[1].with_user(operator),
            kind="rework",
            previous_line_id=lines[0].id,
            reason="Sellado anterior no pasó el ensayo",
        ).action_record()

    def test_pending_proposal_does_not_block_native_closure(self):
        order, operator, supervisor = self._case()
        lines = order.linea_falla_ids
        self._wizard(lines[0].with_user(operator), kind="additional").action_record()
        self._propose(lines, operator)
        order.action_repair_done()
        self.assertEqual(order.state, "done")
        service = self.env["mc.rov.repair.rework.kpi"].with_user(supervisor)
        pending = service.get_summary()
        self.assertEqual((pending["visits_with_rework"], pending["pending_hours"]), (0, 2))
        self.assertIsNone(pending["visit_percent"])
        wizard = self._wizard(lines[1].with_user(supervisor), review=True)
        wizard.action_confirm()
        wizard.action_confirm()
        result = service.get_summary()
        self.assertEqual((result["visits_with_rework"], result["rework_hours"]), (1, 2))
        self.assertEqual((result["visit_percent"], result["hours_percent"]), (100, 40))
        self.assertEqual(result["causes"][0]["key"], "desconocida")
        history = (
            self.env["mc.rov.repair.rework.event"].sudo().search([("line_id", "=", lines[1].id)])
        )
        self.assertEqual(history.actor_id, supervisor | operator)
        self.assertEqual(history.mapped("state"), ["rework", "proposal"])

    def test_taller_cannot_confirm_and_rework_requires_evidence(self):
        order, operator, _supervisor = self._case()
        lines = order.linea_falla_ids
        with self.assertRaises(UserError):
            self._wizard(lines[1].with_user(operator), kind="rework", reason="QA").action_record()
        self._propose(lines, operator)
        with self.assertRaises(AccessError):
            lines[1].with_user(operator).action_mc_confirm_rework()

    def test_changed_proposal_cannot_be_confirmed_from_old_wizard(self):
        order, operator, supervisor = self._case()
        lines = order.linea_falla_ids
        self._propose(lines, operator)
        wizard = self._wizard(lines[1].with_user(supervisor), review=True)
        self._wizard(lines[1].with_user(operator), kind="additional").action_record()
        with self.assertRaises(UserError):
            wizard.action_confirm()
        self.assertEqual(lines[1].with_user(operator).mc_rework_state, "additional")
