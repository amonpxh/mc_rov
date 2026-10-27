from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests.common import new_test_user

from .test_mc_rov_revision import RevisionCommon


class TestWorkCenterInventory(RevisionCommon):
    """El acceso a existencias conserva permisos y acción nativa del usuario."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_user = new_test_user(
            cls.env, login="center_inventory_operator", groups="stock.group_stock_user"
        )
        cls.internal_user = new_test_user(
            cls.env, login="center_inventory_internal", groups="base.group_user"
        )
        cls.portal_user = new_test_user(
            cls.env, login="center_inventory_portal", groups="base.group_portal"
        )

    def _center(self, user=None):
        center = self.env["mc.rov.work.center"].with_user(user or self.stock_user)
        self.assertTrue(hasattr(center, "action_inventory"), "Falta acceso nativo a Inventario")
        return center.with_context(allowed_company_ids=[self.env.company.id])

    def _entry(self, user):
        center = self._center(user)
        entries = [entry for entry in center.get_overview() if entry["topic"] == "inventory"]
        self.assertEqual(len(entries), 1, "Falta capacidad de Inventario")
        return entries[0]

    def test_native_quant_destination_exists(self):
        quant = (
            self.env["stock.quant"]
            .with_user(self.stock_user)
            .with_context(allowed_company_ids=[self.env.company.id], always_show_loc=True)
        )
        action = quant.action_view_quants()
        self.assertEqual(action["res_model"], "stock.quant")
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertTrue(action["context"]["search_default_internal_loc"])

    def test_inventory_available_for_stock_operator_without_quant_count(self):
        entry = self._entry(self.stock_user)
        self.assertTrue(entry["available"])
        self.assertNotIn("count", entry)

    def test_internal_user_without_inventory_group_has_no_access(self):
        self.assertFalse(self._entry(self.internal_user)["available"])
        with self.assertRaises(AccessError):
            self._center(self.internal_user).action_inventory()

    def test_portal_call_is_denied(self):
        with self.assertRaises(AccessError):
            self._center(self.portal_user).action_inventory()

    def test_inventory_action_matches_native_destination_and_views(self):
        center = self._center()
        action = center.action_inventory()
        native = (
            self.env["stock.quant"]
            .with_user(self.stock_user)
            .with_context(center.env.context, always_show_loc=True)
            .action_view_quants()
        )
        for key in ("type", "res_model", "views", "domain", "context"):
            self.assertEqual(action[key], native[key], key)

    def test_stock_operator_does_not_need_technical_action_read_access(self):
        center = self._center()
        self.assertFalse(center.env["ir.actions.act_window"].has_access("read"))
        self.assertEqual(center.action_inventory()["res_model"], "stock.quant")

    def test_inventory_keeps_active_company_context(self):
        center = self._center()
        action = center.action_inventory()
        self.assertEqual(action["context"]["allowed_company_ids"], [self.env.company.id])
        self.assertTrue(action["context"]["always_show_loc"])

    def test_foreign_company_context_is_denied(self):
        company = self.env["res.company"].create({"name": "Inventory forbidden company"})
        center = self._center().with_context(allowed_company_ids=[company.id])
        with self.assertRaises(AccessError):
            center.action_inventory()

    def test_read_acl_is_checked_before_native_action(self):
        center = self._center()
        quant_type = type(center.env["stock.quant"])
        original = quant_type.has_access

        def deny_quant(records, operation):
            if records._name == "stock.quant" and operation == "read":
                return False
            return original(records, operation)

        with patch.object(quant_type, "has_access", deny_quant):
            with patch.object(quant_type, "action_view_quants") as native:
                with self.assertRaises(AccessError):
                    center.action_inventory()
                native.assert_not_called()
