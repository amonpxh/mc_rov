from contextlib import ExitStack
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import new_test_user
from odoo.tools.safe_eval import safe_eval

from .test_mc_rov_revision import RevisionCommon


# Una sola matriz comparte los usuarios y contrasta cada destino con sus permisos nativos.
# pylint: disable-next=too-many-public-methods
class TestWorkCenterInventoryWorkspace(RevisionCommon):
    """El espacio operativo conserva los destinos y límites del Inventario nativo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        features = ",product.group_product_variant,stock.group_production_lot,stock.group_stock_multi_locations"
        cls.operator = new_test_user(
            cls.env,
            login="inventory_workspace_operator",
            groups="stock.group_stock_user" + features,
        )
        cls.manager = new_test_user(
            cls.env,
            login="inventory_workspace_manager",
            groups="stock.group_stock_manager" + features,
        )
        cls.internal = new_test_user(
            cls.env, login="inventory_workspace_internal", groups="base.group_user"
        )
        cls.portal = new_test_user(
            cls.env, login="inventory_workspace_portal", groups="base.group_portal"
        )

    def _center(self, user=None):
        center = (
            self.env["mc.rov.work.center"]
            .with_user(user or self.operator)
            .with_context(allowed_company_ids=[self.env.company.id])
        )
        for method in (
            "get_inventory_destinations",
            "action_inventory_destination",
            "get_inventory_application",
        ):
            self.assertTrue(hasattr(center, method), "Falta espacio operativo de Inventario")
        return center

    def _entries(self, user=None):
        return {entry["key"]: entry for entry in self._center(user).get_inventory_destinations()}

    def _native(self, center, xmlid):
        return self._normalize(center, center.env["ir.actions.actions"]._for_xml_id(xmlid))

    def _normalize(self, center, action):
        action = dict(action)
        values = {
            "uid": center.env.uid,
            "user": center.env.user,
            "allowed_company_ids": center.env.companies.ids,
            "context": dict(center.env.context),
        }
        for field, empty in (("domain", []), ("context", {})):
            value = action.get(field) or empty
            action[field] = safe_eval(value, values) if isinstance(value, str) else value
        action["context"] = {**center.env.context, **action["context"]}
        return action

    def _assert_native(self, key, xmlid):
        center = self._center()
        action = center.action_inventory_destination(key)
        native = self._native(center, xmlid)
        for field in ("type", "res_model", "views", "domain"):
            self.assertEqual(action[field], native[field], field)
        for name, value in native["context"].items():
            self.assertEqual(action["context"][name], value, name)
        self.assertEqual(action["context"]["allowed_company_ids"], [self.env.company.id])

    def _without_group(self, center, xmlid):
        user_type = type(center.env.user)
        original = user_type.has_group
        return patch.object(
            user_type,
            "has_group",
            lambda user, group: False if group == xmlid else original(user, group),
        )

    def _deny_read(self, center, model_name):
        model_type = type(center.env[model_name])
        original = model_type.has_access
        return patch.object(
            model_type,
            "has_access",
            lambda records, operation: (
                False
                if records._name == model_name and operation == "read"
                else original(records, operation)
            ),
        )

    def test_native_products_destination_exists(self):
        action = (
            self.env["ir.actions.actions"]
            .with_user(self.operator)
            ._for_xml_id("stock.product_template_action_product")
        )
        self.assertEqual(action["res_model"], "product.template")
        self.assertIn("kanban", action["view_mode"])

    def test_native_receipts_helper_exists(self):
        action = (
            self.env["stock.picking"]
            .with_user(self.operator)
            .with_context(allowed_company_ids=[self.env.company.id])
            .get_action_picking_tree_incoming()
        )
        self.assertEqual(action["res_model"], "stock.picking")
        self.assertEqual(action["type"], "ir.actions.act_window")

    def test_five_sections_and_nine_explicit_destinations(self):
        entries = self._entries(self.manager)
        self.assertEqual(
            set(entries),
            {
                "stock",
                "products",
                "variants",
                "lots",
                "receipts",
                "deliveries",
                "internal",
                "counts",
                "replenishment",
            },
        )
        self.assertEqual(
            {entry["section"] for entry in entries.values()},
            {"stock", "products", "lots", "operations", "replenishment"},
        )
        self.assertTrue(all(entry["available"] for entry in entries.values()))
        self.assertTrue(all("count" not in entry for entry in entries.values()))

    def test_products_keep_native_catalog_defaults(self):
        self._assert_native("products", "stock.product_template_action_product")

    def test_variants_keep_native_catalog(self):
        self._assert_native("variants", "stock.stock_product_normal_action")

    def test_lots_keep_native_domain_and_grouping(self):
        self._assert_native("lots", "stock.action_production_lot_form")

    def test_receipts_use_native_helper(self):
        center = self._center()
        native = self._normalize(
            center, center.env["stock.picking"].get_action_picking_tree_incoming()
        )
        action = center.action_inventory_destination("receipts")
        for field in ("res_model", "domain", "context", "views"):
            self.assertEqual(action[field], native[field], field)

    def test_deliveries_use_native_helper(self):
        center = self._center()
        native = self._normalize(
            center, center.env["stock.picking"].get_action_picking_tree_outgoing()
        )
        action = center.action_inventory_destination("deliveries")
        for field in ("res_model", "domain", "context", "views"):
            self.assertEqual(action[field], native[field], field)

    def test_internal_transfers_use_native_helper(self):
        center = self._center()
        native = self._normalize(
            center, center.env["stock.picking"].get_action_picking_tree_internal()
        )
        action = center.action_inventory_destination("internal")
        for field in ("res_model", "domain", "context", "views"):
            self.assertEqual(action[field], native[field], field)

    def test_counts_use_physical_inventory_instead_of_stock_report(self):
        center = self._center()
        action = center.action_inventory_destination("counts")
        native = self._normalize(center, center.env["stock.quant"].action_view_inventory())
        for field in ("res_model", "domain", "context", "views"):
            self.assertEqual(action[field], native[field], field)
        self.assertTrue(action["context"]["no_at_date"])

    def test_stock_uses_existing_native_action(self):
        center = self._center()
        action = center.action_inventory_destination("stock")
        native = center.action_inventory()
        for field in ("res_model", "domain", "context", "views"):
            self.assertEqual(action[field], native[field], field)
        self.assertTrue(action["context"]["search_default_internal_loc"])

    def test_replenishment_manager_keeps_native_context(self):
        center = self._center(self.manager)
        seen = []

        def native(records):
            seen.append(dict(records.env.context))
            return {
                "type": "ir.actions.act_window",
                "res_model": "stock.warehouse.orderpoint",
                "context": dict(records.env.context),
            }

        with patch.object(
            type(center.env["stock.warehouse.orderpoint"]), "action_open_orderpoints", native
        ):
            action = center.action_inventory_destination("replenishment")
        self.assertEqual(action["res_model"], "stock.warehouse.orderpoint")
        self.assertEqual(len(seen), 1)
        for key, value in {
            "search_default_filter_to_reorder": True,
            "search_default_filter_not_snoozed": True,
            "default_trigger": "manual",
            "searchpanel_default_trigger": "manual",
            "allowed_company_ids": [self.env.company.id],
        }.items():
            self.assertEqual(seen[0][key], value, key)

    def test_operator_cannot_bypass_manager_replenishment_menu(self):
        center = self._center()
        self.assertTrue(center.env["stock.warehouse.orderpoint"].has_access("read"))
        self.assertFalse(self._entries()["replenishment"]["available"])
        with patch.object(
            type(center.env["stock.warehouse.orderpoint"]), "action_open_orderpoints"
        ) as native:
            with self.assertRaises(AccessError):
                center.action_inventory_destination("replenishment")
            native.assert_not_called()

    def test_internal_non_stock_user_is_denied(self):
        center = self._center(self.internal)
        for method, args in (
            ("get_inventory_destinations", []),
            ("action_inventory_destination", ["products"]),
            ("get_inventory_application", []),
        ):
            with self.subTest(method=method), self.assertRaises(AccessError):
                getattr(center, method)(*args)

    def test_portal_user_is_denied(self):
        center = self._center(self.portal)
        with self.assertRaises(AccessError):
            center.get_inventory_destinations()
        with self.assertRaises(AccessError):
            center.action_inventory_destination("lots")
        with self.assertRaises(AccessError):
            center.get_inventory_application()

    def test_capabilities_never_query_stock_counts_or_run_native_maintenance(self):
        center = self._center(self.manager)

        def forbidden(*args, **kwargs):
            raise AssertionError("Las capacidades no deben consultar ni mantener existencias")

        with ExitStack() as stack:
            for model in (
                "stock.quant",
                "product.template",
                "product.product",
                "stock.lot",
                "stock.picking",
                "stock.warehouse.orderpoint",
            ):
                stack.enter_context(
                    patch.object(type(center.env[model]), "search_count", forbidden)
                )
            stack.enter_context(
                patch.object(type(center.env["stock.quant"]), "_quant_tasks", forbidden)
            )
            stack.enter_context(
                patch.object(
                    type(center.env["stock.warehouse.orderpoint"]),
                    "action_open_orderpoints",
                    forbidden,
                )
            )
            self.assertTrue(center.get_inventory_destinations())

    def test_catalog_opens_without_technical_action_read_permission(self):
        center = self._center()
        self.assertFalse(center.env["ir.actions.act_window"].has_access("read"))
        for key, model in (
            ("products", "product.template"),
            ("variants", "product.product"),
            ("lots", "stock.lot"),
        ):
            self.assertEqual(center.action_inventory_destination(key)["res_model"], model)

    def test_application_selection_does_not_need_technical_menu_read(self):
        center = self._center()
        with patch.object(
            type(center.env["ir.ui.menu"]),
            "read",
            side_effect=AssertionError("No leer menús técnicos"),
        ):
            self.assertEqual(
                center.get_inventory_application()["menu_id"],
                self.env.ref("stock.menu_stock_root").id,
            )

    def test_lots_require_native_tracking_feature(self):
        center = self._center()
        with self._without_group(center, "stock.group_production_lot"):
            self.assertFalse(
                {entry["key"]: entry for entry in center.get_inventory_destinations()}["lots"][
                    "available"
                ]
            )
            with self.assertRaises(AccessError):
                center.action_inventory_destination("lots")

    def test_variants_require_native_variant_feature(self):
        center = self._center()
        with self._without_group(center, "product.group_product_variant"):
            self.assertFalse(
                {entry["key"]: entry for entry in center.get_inventory_destinations()}["variants"][
                    "available"
                ]
            )
            with self.assertRaises(AccessError):
                center.action_inventory_destination("variants")

    def test_internal_transfers_require_native_locations_feature(self):
        center = self._center()
        with self._without_group(center, "stock.group_stock_multi_locations"):
            self.assertFalse(
                {entry["key"]: entry for entry in center.get_inventory_destinations()}["internal"][
                    "available"
                ]
            )
            with self.assertRaises(AccessError):
                center.action_inventory_destination("internal")

    def test_quant_acl_denial_does_not_hide_product_catalog(self):
        center = self._center()
        with self._deny_read(center, "stock.quant"):
            entries = {entry["key"]: entry for entry in center.get_inventory_destinations()}
            self.assertFalse(entries["stock"]["available"])
            self.assertFalse(entries["counts"]["available"])
            self.assertTrue(entries["products"]["available"])
            with self.assertRaises(AccessError):
                center.action_inventory_destination("stock")

    def test_product_read_denial_is_rechecked_on_direct_call(self):
        center = self._center()
        with self._deny_read(center, "product.template"):
            self.assertFalse(
                {entry["key"]: entry for entry in center.get_inventory_destinations()}["products"][
                    "available"
                ]
            )
            with self.assertRaises(AccessError):
                center.action_inventory_destination("products")

    def test_picking_type_read_denial_blocks_native_transfer_helpers(self):
        center = self._center()
        with self._deny_read(center, "stock.picking.type"):
            entries = {entry["key"]: entry for entry in center.get_inventory_destinations()}
            for key in ("receipts", "deliveries", "internal"):
                self.assertFalse(entries[key]["available"])
                with self.assertRaises(AccessError):
                    center.action_inventory_destination(key)

    def test_lot_read_denial_is_rechecked_on_direct_call(self):
        center = self._center()
        with self._deny_read(center, "stock.lot"):
            self.assertFalse(
                {entry["key"]: entry for entry in center.get_inventory_destinations()}["lots"][
                    "available"
                ]
            )
            with self.assertRaises(AccessError):
                center.action_inventory_destination("lots")

    def test_creation_capability_reflects_model_acl(self):
        center = self._center()
        model_type = type(center.env["product.template"])
        original = model_type.has_access
        with patch.object(
            model_type,
            "has_access",
            lambda records, operation: (
                False if operation == "create" else original(records, operation)
            ),
        ):
            entry = {entry["key"]: entry for entry in center.get_inventory_destinations()}[
                "products"
            ]
            self.assertTrue(entry["available"])
            self.assertFalse(entry["can_create"])

    def test_unknown_or_structured_destination_is_rejected(self):
        center = self._center()
        for value in (
            "res.users",
            "stock.action_stock_config_settings",
            129,
            {"xmlid": "stock.action_orderpoint"},
            ["products"],
            False,
        ):
            with self.subTest(value=value), self.assertRaises(UserError):
                center.action_inventory_destination(value)

    def test_foreign_company_context_is_rejected_before_destination(self):
        company = self.env["res.company"].create({"name": "Inventory workspace forbidden company"})
        center = self._center().with_context(allowed_company_ids=[company.id])
        for method, args in (
            ("get_inventory_destinations", []),
            ("action_inventory_destination", ["products"]),
            ("get_inventory_application", []),
        ):
            with self.subTest(method=method), self.assertRaises(AccessError):
                getattr(center, method)(*args)

    def test_selected_companies_survive_native_catalog_actions(self):
        center = self._center()
        for key in ("products", "variants", "lots", "receipts"):
            action = center.action_inventory_destination(key)
            self.assertEqual(action["context"]["allowed_company_ids"], [self.env.company.id])

    def test_capability_lookup_does_not_modify_user_groups(self):
        center = self._center()
        field = "group_ids" if "group_ids" in center.env.user._fields else "groups_id"
        before = set(center.env.user[field].ids)
        center.get_inventory_destinations()
        self.assertEqual(set(center.env.user[field].ids), before)

    def test_application_uses_native_inventory_root(self):
        self.assertEqual(
            self._center().get_inventory_application(),
            {"menu_id": self.env.ref("stock.menu_stock_root").id},
        )

    def test_replenishment_opens_real_native_orderpoint_action(self):
        # El mantenimiento nativo se ejecuta dentro de la transacción de prueba y se revierte.
        center = self._center(self.manager)
        action = center.action_inventory_destination("replenishment")
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "stock.warehouse.orderpoint")
        self.assertTrue(any(view[1] == "list" for view in action["views"]))
        self.assertEqual(action["context"]["allowed_company_ids"], [self.env.company.id])
        self.assertTrue(action["context"]["search_default_filter_to_reorder"])
        self.assertTrue(action["context"]["search_default_filter_not_snoozed"])
        self.assertEqual(action["context"]["default_trigger"], "manual")

    def test_overview_keeps_inventory_when_catalog_is_accessible(self):
        center = self._center()
        with self._deny_read(center, "stock.quant"):
            entry = next(item for item in center.get_overview() if item["topic"] == "inventory")
            self.assertTrue(entry["available"])
