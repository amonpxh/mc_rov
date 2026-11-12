"""La nueva entrada conserva permisos y usa los assets nativos del tablero."""

import ast
from pathlib import Path

from odoo.modules.module import get_module_path
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


class MissingKPIDashboardViews(AssertionError):
    """La presentación ausente no se confunde con un error del runtime."""


@tagged("post_install", "-at_install", "kpi_dashboard_views")
class TestKPIDashboardViews(TransactionCase):
    """El menú y sus assets no conceden acceso nuevo a registros privados."""

    def _action(self):
        action = self.env.ref("mc_rov.action_kpi_dashboard", raise_if_not_found=False)
        if not action:
            raise MissingKPIDashboardViews("Missing native KPI dashboard presentation")
        return action

    def _menu(self):
        self._action()
        menu = self.env.ref("mc_rov.menu_kpi_dashboard", raise_if_not_found=False)
        self.assertTrue(menu)
        return menu

    def _manifest(self):
        self._action()
        path = Path(get_module_path("mc_rov")) / "__manifest__.py"
        return ast.literal_eval(path.read_text(encoding="utf-8"))

    def test_client_action_is_registered(self):
        action = self._action()
        self.assertEqual(action._name, "ir.actions.client")
        self.assertEqual(action.tag, "mc_rov.kpi_dashboard")

    def test_menu_stays_under_work_center(self):
        menu = self._menu()
        self.assertEqual(menu.parent_id, self.env.ref("mc_rov.menu_mc_rov_root"))
        self.assertEqual(menu.action, self._action())

    def test_menu_requires_existing_team_consultation_role(self):
        menu = self._menu()
        field = "group_ids" if "group_ids" in menu._fields else "groups_id"
        self.assertEqual(menu[field], self.env.ref("mc_rov.group_work_assignment_team"))

    def test_dashboard_assets_are_registered(self):
        assets = self._manifest()["assets"]["web.assets_backend"]
        for filename in (
            "presentation.js",
            "loader.js",
            "kpi_dashboard.js",
            "kpi_dashboard.xml",
            "kpi_dashboard.scss",
        ):
            self.assertIn("mc_rov/static/src/kpi_dashboard/" + filename, assets)

    def test_browser_tests_are_registered(self):
        assets = self._manifest()["assets"]["web.assets_unit_tests"]
        self.assertIn("mc_rov/static/tests/kpi_dashboard.test.js", assets)

    def test_existing_work_center_entry_is_preserved(self):
        self._action()
        existing = self.env.ref("mc_rov.menu_mc_rov_work_center")
        self.assertEqual(existing.action.tag, "mc_rov.work_center")

    def test_view_data_file_is_loaded(self):
        data = self._manifest()["data"]
        self.assertIn("views/kpi_dashboard_views.xml", data)
        self.assertGreater(
            data.index("views/kpi_dashboard_views.xml"),
            data.index("views/mc_rov_work_center_views.xml"),
        )

    def test_private_history_models_gain_no_acl(self):
        self._action()
        private = self.env["ir.model"].search(
            [
                (
                    "model",
                    "in",
                    [
                        "mc.rov.repair.acceptance.attempt",
                        "mc.rov.new.acceptance.episode",
                        "mc.rov.new.acceptance.attempt",
                    ],
                )
            ]
        )
        self.assertFalse(self.env["ir.model.access"].search([("model_id", "in", private.ids)]))
