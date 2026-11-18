"""Contratos de asistentes nativos e historial F2, sin ACL general de evidencia."""

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from . import test_detention_capture as capture_contracts
from . import test_detention_boundaries as boundaries
from .acceptance_activity_common import AcceptanceActivityCommon


@tagged("post_install", "-at_install", "detention_presentation")
class TestDetentionPresentation(AcceptanceActivityCommon):
    """Abrir un asistente no concede permisos sobre la orden ni sobre el historial."""

    _service = capture_contracts.TestDetentionCapture._service
    _workshop = capture_contracts.TestDetentionCapture._workshop
    _order = capture_contracts.TestDetentionCapture._order
    _start = capture_contracts.TestDetentionCapture._start
    _history = capture_contracts.TestDetentionCapture._history
    _rule = boundaries.TestDetentionBoundaries._rule

    def _feature(self):
        self.assertTrue(
            "mc.rov.detention.wizard" in self.env.registry.models,
            "Falta interfaz nativa F2",
        )
        return self.env["mc.rov.detention.wizard"]

    def _wizard(self, service, source, decision="start", **values):
        method = (
            source.with_user(service.env.user).action_open_detention_start
            if decision == "start"
            else source.with_user(service.env.user).action_open_detention_finish
        )
        action = method()
        return (
            self._feature()
            .with_user(service.env.user)
            .with_context(**action["context"])
            .create(
                {
                    "decision": decision,
                    **values,
                }
            )
        )

    def test_repair_action_preserves_authorized_source(self):
        self._feature()
        service = self._service()
        order = self._order()
        action = order.with_user(service.env.user).action_open_detention_start()
        self.assertEqual(action["res_model"], "mc.rov.detention.wizard")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"]["default_repair_id"], order.id)
        self.assertFalse(action["context"].get("default_production_id"))
        self.assertFalse(self._history(service, order))

    def test_manufacturing_action_preserves_authorized_source(self):
        self._feature()
        service = self._service()
        order = self._production()
        order.action_confirm()
        action = order.with_user(service.env.user).action_open_detention_start()
        self.assertEqual(action["context"]["default_production_id"], order.id)
        self.assertFalse(action["context"].get("default_repair_id"))

    def test_start_wizard_records_fact_without_changing_order(self):
        self._feature()
        service = self._service()
        order = self._order()
        original = order.state
        wizard = self._wizard(
            service,
            order,
            cause="materials",
            responsible_employee_id=self.empleado.id,
            explanation="QA no permite avanzar",
        )
        result = wizard.action_apply()
        self.assertEqual(result["type"], "ir.actions.act_window_close")
        self.assertEqual(order.state, original)
        rows = self._history(service, order)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["actor_id"], service.env.uid)
        self.assertEqual(rows[0]["responsible_employee_id"], self.empleado.id)

    def test_finish_wizard_preserves_identity_and_start(self):
        self._feature()
        service = self._service()
        order = self._order()
        identity = self._start(service, order)
        original = self._history(service, order)[0]
        wizard = self._wizard(
            service,
            order,
            "finish",
            interval_key=str(identity),
            explanation="QA material disponible",
        )
        wizard.action_apply()
        current = self._history(service, order)[0]
        self.assertEqual(current["id"], original["id"])
        self.assertEqual(current["started_at"], original["started_at"])
        self.assertEqual(current["actor_id"], original["actor_id"])
        self.assertEqual(current["end_kind"], "resumed")
        self.assertTrue(current["ended_at"])
        self.assertEqual(order.state, "confirmed")

    def test_other_still_requires_explanation(self):
        self._feature()
        service = self._service()
        wizard = self._wizard(
            service,
            self._order(),
            cause="other",
            responsible_employee_id=self.empleado.id,
        )
        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_forged_default_context_cannot_finish_another_source(self):
        model = self._feature()
        service = self._service()
        own, other = self._order(), self._order()
        identity = self._start(service, other)
        wizard = (
            model.with_user(service.env.user)
            .with_context(default_repair_id=other.id)
            .create(
                {
                    "decision": "finish",
                    "repair_id": own.id,
                    "interval_key": str(identity),
                }
            )
        )
        with self.assertRaises(AccessError):
            wizard.action_apply()
        self.assertFalse(self._history(service, other)[0]["ended_at"])

    def test_read_only_source_cannot_open_registration(self):
        self._feature()
        service = self._service()
        order = self._order()
        self._rule(perm_write=True)
        with self.assertRaises(AccessError):
            order.with_user(service.env.user).action_open_detention_start()

    def test_revoked_source_read_cannot_render_history(self):
        self._feature()
        service = self._service()
        order = self._order()
        self._start(service, order)
        self._rule(perm_read=True)
        with self.assertRaises(AccessError):
            _html = order.with_user(service.env.user).mc_detention_history_html

    def test_portal_cannot_create_wizard(self):
        model = self._feature()
        portal = new_test_user(
            self.env, login="qa_detention_wizard_portal", groups="base.group_portal"
        )
        with self.assertRaises(AccessError):
            model.with_user(portal).create({"repair_id": self._order().id, "decision": "start"})

    def test_foreign_company_context_cannot_open_wizard(self):
        self._feature()
        service = self._service()
        order = self._order()
        foreign = self.env["res.company"].create({"name": "QA F2 otra empresa de contexto"})
        with self.assertRaises(AccessError):
            order.with_user(service.env.user).with_context(
                allowed_company_ids=foreign.ids
            ).action_open_detention_start()

    def test_history_escapes_explanation_as_text(self):
        self._feature()
        service = self._service()
        order = self._order()
        self._start(service, order, cause="other", explanation="<script>QA F2</script>")
        html = str(order.with_user(service.env.user).mc_detention_history_html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_native_source_views_expose_detention_page(self):
        self._feature()
        for identity in ("view_repair_detentions", "view_production_detentions"):
            view = self.env.ref("mc_rov." + identity)
            arch = view._get_combined_arch()
            self.assertEqual(len(arch.xpath("//page[@name='mc_detentions']")), 1)
            self.assertTrue(arch.xpath("//button[@name='action_open_detention_start']"))
            self.assertTrue(arch.xpath("//field[@name='mc_detention_history_html']"))
