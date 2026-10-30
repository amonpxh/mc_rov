"""Operaciones y calendario propios; no depender de almacenes o datos de ejemplo."""

from datetime import datetime
from unittest.mock import patch

import pytz

from odoo import Command
from odoo.tests.common import TransactionCase, new_test_user


class InventoryActivityCommon(TransactionCase):
    """Entradas/salidas/internos nativos, sin validar movimientos ni alterar stock."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context={
                **cls.env.context,
                "no_reset_password": True,
                "mail_create_nosubscribe": True,
                "tracking_disable": True,
            }
        )
        cls.operator = new_test_user(
            cls.env, login="qa_inventory_operator", groups="stock.group_stock_user"
        )
        cls.coordinator = new_test_user(
            cls.env,
            login="qa_inventory_coordinator",
            groups="stock.group_stock_user,mc_rov.group_work_assignment_coordinate",
        )
        cls.outsider = new_test_user(
            cls.env, login="qa_inventory_outsider", groups="base.group_user"
        )
        cls.calendar = cls.env["resource.calendar"].create(
            {
                "name": "QA Inventario Santiago",
                "company_id": cls.env.company.id,
                "tz": "America/Santiago",
                "attendance_ids": [
                    Command.clear(),
                    *[
                        Command.create(
                            {
                                "name": "QA jornada",
                                "dayofweek": str(day),
                                "hour_from": 8,
                                "hour_to": 17,
                                "day_period": "morning",
                            }
                        )
                        for day in range(5)
                    ],
                ],
            }
        )
        cls.locations = {}
        for key, usage in (
            ("supplier", "supplier"),
            ("stock", "internal"),
            ("other_stock", "internal"),
            ("customer", "customer"),
        ):
            cls.locations[key] = cls.env["stock.location"].create(
                {
                    "name": "QA Inventario " + key,
                    "usage": usage,
                    "company_id": cls.env.company.id if usage == "internal" else False,
                }
            )
        cls.types = {}
        for code, source, target in (
            ("incoming", "supplier", "stock"),
            ("outgoing", "stock", "customer"),
            ("internal", "stock", "other_stock"),
        ):
            cls.types[code] = cls.env["stock.picking.type"].create(
                {
                    "name": "QA Inventario " + code,
                    "code": code,
                    "sequence_code": "QAI" + code[:1].upper(),
                    "company_id": cls.env.company.id,
                    "warehouse_id": False,
                    "default_location_src_id": cls.locations[source].id,
                    "default_location_dest_id": cls.locations[target].id,
                }
            )
        category = cls.env["product.category"].create({"name": "QA Componente logístico"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "QA Componente de inventario",
                "type": "consu",
                "is_storable": True,
                "categ_id": category.id,
                "company_id": cls.env.company.id,
            }
        )

    def _picking(self, code="incoming", **values):
        kind = self.types[code]
        return self.env["stock.picking"].create(
            {
                "picking_type_id": kind.id,
                "location_id": kind.default_location_src_id.id,
                "location_dest_id": kind.default_location_dest_id.id,
                "move_ids": [
                    Command.create(
                        {
                            "name": "QA Movimiento real",
                            "product_id": self.product.id,
                            "product_uom_qty": 2,
                            "product_uom": self.product.uom_id.id,
                            "location_id": kind.default_location_src_id.id,
                            "location_dest_id": kind.default_location_dest_id.id,
                        }
                    )
                ],
                **values,
            }
        )

    def _policy_model(self):
        self.assertTrue(
            "mc.rov.inventory.activity.policy" in self.env.registry.models,
            "Missing inventory activity policy",
        )
        return self.env["mc.rov.inventory.activity.policy"]

    def _policy(self, **values):
        return self._policy_model().create(
            {
                "company_id": self.env.company.id,
                "enabled": True,
                "calendar_id": self.calendar.id,
                **values,
            }
        )

    def _rule(self, picking_type=None, policy=None, **values):
        policy = policy or self._policy()
        self.assertIn(
            "mc.rov.inventory.activity.rule",
            self.env.registry.models,
            "Missing inventory activity rule",
        )
        return self.env["mc.rov.inventory.activity.rule"].create(
            {
                "policy_id": policy.id,
                "picking_type_id": (picking_type or self.types["incoming"]).id,
                "user_id": self.operator.id,
                **values,
            }
        )

    def _configured(self, **values):
        policy = self._policy(**values)
        self._rule(policy=policy)
        return policy, self._picking()

    def _other_company(self):
        with patch.object(
            type(self.env["res.company"]), "_create_internal_project_task", create=True
        ):
            return self.env["res.company"].create({"name": "QA Inventario otra empresa"})

    def _other_type(self, company):
        return self.env["stock.picking.type"].create(
            {
                "name": "QA Operación otra empresa",
                "code": "incoming",
                "sequence_code": "QAOT",
                "company_id": company.id,
                "warehouse_id": False,
            }
        )

    def _holiday(self):
        zone = pytz.timezone(self.calendar.tz)
        self.env["resource.calendar.leaves"].create(
            {
                "name": "QA excepción lunes",
                "calendar_id": self.calendar.id,
                "company_id": self.env.company.id,
                "resource_id": False,
                "date_from": zone.localize(datetime(2026, 11, 2))
                .astimezone(pytz.utc)
                .replace(tzinfo=None),
                "date_to": zone.localize(datetime(2026, 11, 3))
                .astimezone(pytz.utc)
                .replace(tzinfo=None),
            }
        )
