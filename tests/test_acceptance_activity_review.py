from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .acceptance_activity_common import AcceptanceActivityCommon


@tagged("post_install", "-at_install")
class TestAcceptanceActivityReview(AcceptanceActivityCommon):
    """El seguimiento apagado no añade permisos al cierre nativo de fabricación."""

    def _prepared(self, mode):
        policy = self._acceptance_policy()
        policies = self.env["mc.rov.acceptance.activity.policy"]
        if mode == "absent":
            policy.unlink()
            self.assertFalse(policies.search([("company_id", "=", self.env.company.id)]))
        elif mode == "disabled":
            policy.enabled = False
        controls = self.env["mc.rov.automation.control"]
        control = controls.search([("company_id", "=", self.env.company.id)], limit=1)
        values = {"enabled": mode != "paused"}
        if control:
            control.write(values)
        else:
            controls.create(dict(values, company_id=self.env.company.id))
        user = new_test_user(
            self.env,
            login="qa_acceptance_read_only_lot",
            groups="mrp.group_mrp_user,stock.group_stock_user",
        )
        production = self._production()
        production.action_confirm()
        lot = self._serials()
        production.write({"lot_producing_ids": [Command.set(lot.ids)], "qty_producing": 1})
        self.env["ir.rule"].create(
            {
                "name": "QA lote legible sin escritura",
                "model_id": self.env["ir.model"]._get_id("stock.lot"),
                "domain_force": repr([("id", "!=", lot.id)]),
                "perm_read": False,
                "perm_write": True,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        self.env.invalidate_all()
        lot.with_user(user).check_access("read")
        with self.assertRaises(AccessError):
            lot.with_user(user).check_access("write")
        production.with_user(user).check_access("write")
        return production.with_user(user), lot

    def _finish_untracked(self, mode):
        production, lot = self._prepared(mode)
        try:
            production.with_context(skip_redirection=True).button_mark_done()
        except AccessError as error:
            self.fail(f"El seguimiento {mode} bloqueó el cierre nativo: {error}")
        self.assertEqual(production.state, "done")
        self.assertFalse(
            self.env["mc.rov.acceptance.activity.cycle"].search(
                [("production_id", "=", production.id), ("lot_id", "=", lot.id)]
            )
        )
        return production

    def test_native_completion_allows_read_only_lot_without_acceptance_hooks(self):
        production, _lot = self._prepared("absent")
        # Control: comprobar primero que la regla no impide el cierre de MRP por sí misma.
        service = self.env["mc.rov.acceptance.activity.automation"]
        with patch.object(type(service), "_after_completion", return_value=None):
            production.with_context(skip_redirection=True).button_mark_done()
        self.assertEqual(production.state, "done")

    def test_absent_acceptance_does_not_require_lot_write(self):
        production = self._finish_untracked("absent")
        self.assertTrue(
            production.message_ids.filtered(
                lambda message: "aceptación" in (message.body or "").lower()
            ),
            "La orden debe conservar el aviso de configuración ausente",
        )

    def test_disabled_acceptance_does_not_require_lot_write(self):
        self._finish_untracked("disabled")

    def test_paused_acceptance_does_not_require_lot_write(self):
        self._finish_untracked("paused")

    def test_enabled_acceptance_keeps_original_actor_lot_write_check(self):
        production, lot = self._prepared("enabled")
        with self.assertRaises(AccessError), self.cr.savepoint():
            production.with_context(skip_redirection=True).button_mark_done()
        self.assertFalse(
            self.env["mc.rov.acceptance.activity.cycle"].search(
                [("production_id", "=", production.id), ("lot_id", "=", lot.id)]
            )
        )
