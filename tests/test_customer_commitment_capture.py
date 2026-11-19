"""Contratos nativos de captura, origen y conservación de promesas F3."""

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user

from ..models.stock_lot import ROV_CATEG_PARAM


@tagged("post_install", "-at_install", "customer_commitment_capture")
class TestCustomerCommitmentCapture(TransactionCase):
    """Comprueba el flujo del asistente con documentos y permisos nativos."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        category = cls.env["product.category"].create({"name": "QA Promesas ROV"})
        cls.env["ir.config_parameter"].set_param(ROV_CATEG_PARAM, str(category.id))
        cls.product = cls.env["product.product"].create(
            {
                "name": "QA ROV comprometido",
                "categ_id": category.id,
                "is_storable": True,
                "tracking": "serial",
            }
        )
        cls.lots = cls.env["stock.lot"].create(
            [
                {"name": serial, "product_id": cls.product.id}
                for serial in ("QA-PROMESA-01", "QA-PROMESA-02")
            ]
        )
        cls.partner = cls.env["res.partner"].create({"name": "QA Cliente F3"})
        cls.supervisor = new_test_user(
            cls.env,
            login="qa_f3_supervisor",
            groups="sales_team.group_sale_manager,stock.group_stock_manager,"
            "mc_rov.group_customer_commitment_supervisor",
        )
        cls.sale = cls.env["sale.order"].create({"partner_id": cls.partner.id})
        cls.line = cls.env["sale.order.line"].create(
            {"order_id": cls.sale.id, "product_id": cls.product.id, "product_uom_qty": 2}
        )
        cls.repair = cls.env["repair.order"].create(
            {
                "partner_id": cls.partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "lot_id": cls.lots[0].id,
            }
        )

    def _wizard(self, source, **overrides):
        source = source.with_user(self.supervisor)
        self.assertTrue(
            callable(getattr(source, "action_mc_customer_commitment", None)),
            "Falta la acción de captura F3.",
        )
        action = source.action_mc_customer_commitment()
        wizard = source.env[action["res_model"]].with_context(**action["context"])
        return wizard.create(
            {
                "sale_line_id": self.line.id if source._name == "sale.order" else False,
                "precision": "day",
                "promised_date": "2026-12-01",
                "agreed_at": "2024-10-01 12:00:00",
                "evidence": "Acta de aceptación QA",
                **overrides,
            }
        )

    def _commitments(self):
        return (
            self.env["mc.rov.customer.commitment"]
            .sudo()
            .search([("company_id", "=", self.sale.company_id.id)])
        )

    def test_sale_scope_is_immutable_and_double_submission_keeps_one_promise(self):
        wizard = self._wizard(self.sale, lot_ids=[Command.set(self.lots.ids)])
        wizard.action_apply()
        wizard.action_apply()
        row = self._commitments()
        self.assertEqual(len(row), 1)
        self.assertEqual(row._commitment_source(), self.sale)
        self.assertEqual(row.quantity, 2)
        self.assertEqual(row.lot_ids, self.lots)
        self.assertEqual(row.actor_id, self.supervisor)
        with self.assertRaises(AccessError):
            row.write({"quantity": 1})
        with self.assertRaises(AccessError):
            row.unlink()

    def test_changes_keep_original_and_cancel_is_an_immutable_event(self):
        self._wizard(self.repair).action_apply()
        self._wizard(
            self.repair,
            operation="reprogram",
            promised_date="2026-12-02",
            agreed_at="2024-10-02 12:00:00",
            reason="Ventana de retiro acordada",
        ).action_apply()
        cancel = self._wizard(
            self.repair,
            operation="cancel",
            agreed_at="2024-10-03 12:00:00",
            reason="Cancelación acordada",
        )
        cancel.action_apply()
        cancel.action_apply()
        row = self._commitments()
        self.assertEqual(row.promised_date, fields.Date.to_date("2026-12-01"))
        self.assertEqual(row.change_ids.mapped("kind"), ["reprogram", "cancel"])
        self.assertEqual(row.change_ids[0].promised_date, fields.Date.to_date("2026-12-02"))
        self.assertFalse(row.change_ids[1].promised_date)
        with self.assertRaises(AccessError):
            row.change_ids[0].write({"reason": "Sobrescritura"})

    def test_rejects_series_of_a_different_product(self):
        other = self.env["product.product"].create(
            {
                "name": "QA Otro ROV",
                "categ_id": self.product.categ_id.id,
                "is_storable": True,
                "tracking": "serial",
            }
        )
        wrong_lot = self.env["stock.lot"].create(
            {"name": "QA-FUERA-DEL-ALCANCE", "product_id": other.id}
        )
        wizard = self._wizard(self.sale, lot_ids=[Command.set((wrong_lot | self.lots[0]).ids)])
        with self.assertRaises(UserError):
            wizard.action_apply()
        self.assertFalse(self._commitments())

    def test_selected_series_can_cover_part_of_the_scope(self):
        wizard = self._wizard(self.sale, lot_ids=[Command.set(self.lots[0].ids)])
        wizard.action_apply()
        row = self._commitments()
        self.assertEqual(row.quantity, 2)
        self.assertEqual(row.lot_ids, self.lots[0])

    def test_supervisor_role_cannot_replace_native_sale_write(self):
        supervisor = new_test_user(
            self.env,
            login="qa_f3_supervisor_sin_venta",
            groups="base.group_user,mc_rov.group_customer_commitment_supervisor",
        )
        with self.assertRaises(AccessError):
            self.sale.with_user(supervisor).action_mc_customer_commitment()

    def test_native_sale_write_cannot_replace_supervisor_role(self):
        seller = new_test_user(
            self.env,
            login="qa_f3_venta_sin_supervision",
            groups="sales_team.group_sale_manager",
        )
        with self.assertRaises(AccessError):
            self.sale.with_user(seller).action_mc_customer_commitment()

    def test_sale_reader_can_view_history_without_private_model_access(self):
        self._wizard(self.sale).action_apply()
        seller = new_test_user(
            self.env,
            login="qa_f3_lector_venta",
            groups="sales_team.group_sale_manager",
        )
        source = self.sale.with_user(seller)
        action = source.action_mc_customer_commitments()
        history = source.env[action["res_model"]].browse(action["res_id"])
        self.assertIn("Acta de aceptación QA", history.content)
        with self.assertRaises(AccessError):
            self._commitments().with_user(seller).read(["evidence"])

    def test_context_defaults_cannot_insert_a_change_into_the_ledger(self):
        wizard = self._wizard(self.sale)
        wizard.with_context(
            default_change_ids=[
                Command.create(
                    {
                        "kind": "cancel",
                        "agreed_at": "2024-10-02 12:00:00",
                        "actor_id": self.supervisor.id,
                        "evidence": "QA",
                        "reason": "Inyección de contexto",
                    }
                )
            ]
        ).action_apply()
        self.assertFalse(self._commitments().change_ids)

    def test_wizard_rejects_inaccessible_sales_reference_before_read(self):
        supervisor = new_test_user(
            self.env,
            login="qa_f3_wizard_without_sales",
            groups="base.group_user,mc_rov.group_customer_commitment_supervisor",
        )
        model = self.env["mc.rov.customer.commitment.wizard"].with_user(supervisor)
        self.assertFalse(self.sale.with_user(supervisor).has_access("write"))
        with self.assertRaises(AccessError):
            model.create(
                {
                    "sale_id": self.sale.id,
                    "sale_line_id": self.line.id,
                    "evidence": "Acta ficticia",
                }
            )

    def test_later_native_sale_link_keeps_repair_origin_and_excludes_duplicate(self):
        self._wizard(self.repair).action_apply()
        service = self.env["product.product"].create({"name": "QA Servicio F3", "type": "service"})
        line = self.env["sale.order.line"].create(
            {"order_id": self.sale.id, "product_id": service.id, "product_uom_qty": 1}
        )
        self.repair.write({"sale_order_id": self.sale.id, "sale_order_line_id": line.id})
        with self.assertRaises(UserError):
            self._wizard(self.sale, sale_line_id=line.id).action_apply()
        row = self._commitments()
        self.assertEqual(len(row), 1)
        self.assertEqual(row._commitment_source(), self.repair)
        self.assertFalse(row.sale_line_id)
        self.assertEqual(row.repair_id.sale_order_id, self.sale)

    def test_sale_service_scope_uses_the_linked_repair_product_and_serial(self):
        service = self.env["product.product"].create({"name": "QA Servicio F3", "type": "service"})
        line = self.env["sale.order.line"].create(
            {"order_id": self.sale.id, "product_id": service.id, "product_uom_qty": 1}
        )
        self.repair.write({"sale_order_id": self.sale.id, "sale_order_line_id": line.id})
        self._wizard(self.sale, sale_line_id=line.id).action_apply()
        row = self._commitments()
        self.assertEqual(row._commitment_source(), self.sale)
        self.assertEqual(row.repair_id, self.repair)
        self.assertEqual(row.product_id, self.product)
        self.assertEqual(row.lot_ids, self.lots[0])
