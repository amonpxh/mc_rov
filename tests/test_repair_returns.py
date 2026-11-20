"""Q2 separa el vínculo de Taller del dictamen del Supervisor."""

from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user

from .test_customer_commitment_browser import dispatch_wizard, prepare_f3_case
from .test_repair_lead_time import arrival_wizard, receive_rov


@tagged("post_install", "-at_install", "repair_returns")
class TestRepairReturns(TransactionCase):
    """Visitas, movimientos y actores ficticios con los permisos nativos."""

    def _case(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        original, outgoing, attachment = prepare_f3_case(self.env, warehouse, "Q2")
        returned = self.env["repair.order"].create(
            {
                field: original[field].id
                for field in ("company_id", "product_id", "product_uom", "lot_id", "partner_id")
            }
        )
        receipt = receive_rov(self.env, warehouse, returned)
        base_groups = "stock.group_stock_manager,mc_rov.group_work_assignment_team"
        operator = new_test_user(self.env, login="qa_q2_taller", groups=base_groups)
        supervisor = new_test_user(
            self.env,
            login="qa_q2_supervisor",
            groups=base_groups
            + ",mc_rov.group_repair_return_supervisor,mc_rov.group_customer_commitment_supervisor",
        )
        dispatch_wizard(
            outgoing.with_user(supervisor),
            original,
            attachment,
            fields.Datetime.now() - timedelta(days=2),
        ).action_apply()
        arrival_wizard(returned.with_user(operator), receipt).action_apply()
        return original, returned.with_user(operator), supervisor

    def _wizard(self, returned, **values):
        return returned.env["mc.rov.repair.return.wizard"].create(
            {"return_id": returned.id, **values}
        )

    def test_link_once_and_confirm_with_distinct_roles(self):
        original, returned, supervisor = self._case()
        link = self._wizard(returned, original_id=original.id)
        link.action_link()
        link.action_link()
        self.assertEqual(returned.mc_return_relation, "pending")
        decision = self._wizard(returned, relation="confirmed", reason="Misma falla documentada")
        with self.assertRaises(AccessError):
            decision.action_decide()
        self._wizard(
            returned.with_user(supervisor), relation="confirmed", reason="Misma falla documentada"
        ).action_decide()
        self.assertEqual(returned.mc_return_relation, "confirmed")
        entry = self.env["mc.rov.repair.return"].sudo().search([("return_id", "=", returned.id)])
        self.assertEqual(entry.linked_by, returned.env.user)
        self.assertEqual(entry.decided_by, supervisor)

    def test_requires_distinct_visits_and_documented_decision(self):
        original, returned, supervisor = self._case()
        with self.assertRaises(UserError):
            self._wizard(returned, original_id=returned.id).action_link()
        self._wizard(returned, original_id=original.id).action_link()
        with self.assertRaises(UserError):
            self._wizard(returned.with_user(supervisor), relation="unrelated").action_decide()
        self._wizard(
            returned.with_user(supervisor), relation="unrelated", reason="Daño nuevo"
        ).action_decide()
        report = returned.env["mc.rov.repair.return"].get_summary()
        self.assertEqual(report["observed_unrelated_returns"], 1)
        self.assertNotIn("value", report)

    def test_supervisor_requires_read_access_to_original_visit(self):
        original, returned, supervisor = self._case()
        self._wizard(returned, original_id=original.id).action_link()
        self.env["ir.rule"].create(
            {
                "name": "QA Q2 restringe la visita original",
                "model_id": self.env["ir.model"]._get_id("repair.order"),
                "domain_force": repr([("id", "!=", original.id)]),
            }
        )
        restricted = returned.with_user(supervisor)
        self.assertFalse(original.with_user(supervisor).has_access("read"))
        self.assertFalse(restricted.mc_return_relation)
        with self.assertRaises(AccessError):
            self._wizard(restricted, relation="unrelated", reason="Daño nuevo").action_decide()
        self.assertEqual(
            restricted.env["mc.rov.repair.return"].get_summary()["observed_returns"], 0
        )
