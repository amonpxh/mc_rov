"""Matriz F2 adicional: autorización efectiva, empresas e identidad del historial."""

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from . import test_detention_capture as capture_contracts
from .acceptance_activity_common import AcceptanceActivityCommon


@tagged("post_install", "-at_install", "detention_boundaries")
class TestDetentionBoundaries(AcceptanceActivityCommon):
    """Ejercita fronteras reales sin otorgar permisos nuevos sobre las órdenes."""

    _service = capture_contracts.TestDetentionCapture._service
    _workshop = capture_contracts.TestDetentionCapture._workshop
    _order = capture_contracts.TestDetentionCapture._order
    _start = capture_contracts.TestDetentionCapture._start
    _history = capture_contracts.TestDetentionCapture._history

    def _rule(self, **values):
        return self.env["ir.rule"].create(
            {
                "name": "QA F2 frontera de origen",
                "model_id": self.env["ir.model"]._get_id("repair.order"),
                "domain_force": '[("id", "=", 0)]',
                "perm_read": False,
                "perm_write": False,
                "perm_create": False,
                "perm_unlink": False,
                **values,
            }
        )

    def test_company_transfer_with_history_explains_refusal(self):
        service = self._service()
        order = self._order()
        self._start(service, order)
        company = order.company_id
        foreign = self.env["res.company"].create({"name": "QA F2 transferencia"})
        with self.assertRaisesRegex(UserError, "No cambie la empresa"):
            order.write({"company_id": foreign.id})
        self.assertEqual(order.company_id, company)
        self.assertEqual(len(self._history(service, order)), 1)

    def test_company_transfer_remains_protected_after_interval_ends(self):
        service = self._service()
        order = self._order()
        identity = self._start(service, order)
        service.finish_detention(identity, "Resuelto QA")
        foreign = self.env["res.company"].create({"name": "QA F2 historia cerrada"})
        with self.assertRaisesRegex(UserError, "No cambie la empresa"):
            order.write({"company_id": foreign.id})

    def test_read_only_source_allows_history_but_not_completion(self):
        service = self._service()
        order = self._order()
        identity = self._start(service, order)
        self._rule(perm_write=True)
        self.assertEqual(len(self._history(service, order)), 1)
        with self.assertRaises(AccessError):
            service.finish_detention(identity, "No autorizado")

    def test_read_only_source_cannot_register_another_cause(self):
        service = self._service()
        order = self._order()
        self._rule(perm_write=True)
        with self.assertRaises(AccessError):
            self._start(service, order, cause="client")

    def test_revoked_source_read_access_hides_history(self):
        service = self._service()
        order = self._order()
        self._start(service, order)
        self._rule(perm_read=True)
        with self.assertRaises(AccessError):
            self._history(service, order)

    def test_portal_cannot_query_history(self):
        self._service()
        order = self._order()
        portal = new_test_user(self.env, login="qa_detention_portal", groups="base.group_portal")
        with self.assertRaises(AccessError):
            self._history(self._service(portal), order)

    def test_foreign_employee_cannot_be_assigned(self):
        service = self._service()
        order = self._order()
        foreign = self.env["res.company"].create({"name": "QA F2 empleado externo"})
        employee = self.env["hr.employee"].create(
            {"name": "QA F2 otra empresa", "company_id": foreign.id}
        )
        with self.assertRaises(AccessError):
            service.start_detention(order._name, order.id, "materials", employee.id, "QA")

    def test_boolean_and_negative_source_ids_are_rejected(self):
        service = self._service()
        for identity in (True, False, 0, -1):
            with self.subTest(identity=identity), self.assertRaises(ValidationError):
                service.get_intervals("repair.order", identity)

    def test_unexpected_model_argument_is_rejected(self):
        service = self._service()
        for model in ("res.users", [], None):
            with self.subTest(model=model), self.assertRaises(ValidationError):
                service.get_intervals(model, 1)

    def test_incoherent_company_is_rejected_instead_of_hidden(self):
        service = self._service()
        order = self._order()
        identity = self._start(service, order)
        foreign = self.env["res.company"].create({"name": "QA F2 incoherencia"})
        # Solo el registro ficticio propio: simula corrupción externa al ORM protegido.
        history = self.env["mc.rov.detention.interval"].sudo().browse(identity)
        history.flush_recordset(["company_id"])
        self.env.cr.execute(
            "UPDATE mc_rov_detention_interval SET company_id=%s WHERE id=%s",
            [foreign.id, identity],
        )
        history.invalidate_recordset(["company_id"])
        with self.assertRaises(AccessError):
            self._history(service, order)
        with self.assertRaises(AccessError):
            service.finish_detention(identity, "No ocultar evidencia ajena")
