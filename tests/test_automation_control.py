from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from . import test_repair_activity_lifecycle as repair_tests
from .test_mc_rov_revision import RevisionCommon


@tagged("post_install", "-at_install")
class TestAutomationControl(RevisionCommon):
    """Pausar pendientes nuevos sin detener el negocio ni sus cierres existentes."""

    _policy = repair_tests.TestRepairActivityLifecycle._policy
    _order = repair_tests.TestRepairActivityLifecycle._order
    _runs = repair_tests.TestRepairActivityLifecycle._runs
    _visit = repair_tests.TestRepairActivityLifecycle._visit
    _confirm = repair_tests.TestRepairActivityLifecycle._confirm

    def _control_model(self):
        self.assertIn(
            "mc.rov.automation.control",
            self.env.registry.models,
            "Missing shared automation creation control",
        )
        return self.env["mc.rov.automation.control"]

    def _control(self, company=None, **values):
        model = self._control_model()
        company = company or self.env.company
        values = {"enabled": True, **values}
        row = model.search([("company_id", "=", company.id)])
        if row:
            row.write(values)
            return row
        return model.create({"company_id": company.id, **values})

    def _coordinator(self):
        return new_test_user(
            self.env,
            login="qa_automation_coordinator",
            groups="base.group_user,mc_rov.group_work_assignment_coordinate",
            company_id=self.env.company.id,
            company_ids=[Command.set(self.env.company.ids)],
        )

    def test_missing_control_keeps_creation_enabled(self):
        model = self._control_model()
        company = self.env["res.company"].create({"name": "QA sin control general"})
        self.assertFalse(model.search([("company_id", "=", company.id)]))
        self.assertTrue(model._creation_enabled(company))

    def test_control_is_enabled_by_default(self):
        model = self._control_model()
        company = self.env["res.company"].create({"name": "QA valor predeterminado"})
        row = model.create({"company_id": company.id})
        self.assertTrue(row.enabled)
        self.assertTrue(row._creation_enabled(company))

    def test_disabled_control_stops_creation(self):
        row = self._control(enabled=False)
        self.assertFalse(row._creation_enabled(self.env.company))
        row.enabled = True
        self.assertTrue(row._creation_enabled(self.env.company))

    def test_one_control_per_company(self):
        row = self._control()
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            row.create({"company_id": self.env.company.id})

    def test_other_company_is_independent(self):
        row = self._control(enabled=False)
        other = self.env["res.company"].create({"name": "QA otra empresa seguimiento"})
        self.assertTrue(row._creation_enabled(other))
        self._control(other, enabled=True)
        self.assertFalse(row._creation_enabled(self.env.company))

    def test_coordinator_can_pause_own_company(self):
        row = self._control()
        coordinator = self._coordinator()
        row.with_user(coordinator).write({"enabled": False})
        self.assertFalse(row.enabled)

    def test_coordinator_cannot_edit_other_company(self):
        self._control_model()
        coordinator = self._coordinator()
        other = self.env["res.company"].create({"name": "QA control ajeno"})
        row = self._control(other)
        with self.assertRaises(AccessError), self.cr.savepoint():
            row.with_user(coordinator).with_context(
                allowed_company_ids=self.env.company.ids
            ).write({"enabled": False})
        self.assertTrue(row.enabled)

    def test_operator_cannot_read_or_edit_control(self):
        row = self._control()
        operator = new_test_user(
            self.env,
            login="qa_automation_operator",
            groups="base.group_user",
            company_id=self.env.company.id,
        )
        with self.assertRaises(AccessError), self.cr.savepoint():
            row.with_user(operator).read(["enabled"])
        with self.assertRaises(AccessError), self.cr.savepoint():
            row.with_user(operator).write({"enabled": False})

    def test_menu_is_configuration_followup_and_reuses_repair_action(self):
        self._control_model()
        root = self.env.ref("mc_rov.menu_mc_rov_root")
        settings = self.env.ref("mc_rov.menu_work_configuration", raise_if_not_found=False)
        followup = self.env.ref("mc_rov.menu_work_automation", raise_if_not_found=False)
        general = self.env.ref("mc_rov.menu_work_automation_control", raise_if_not_found=False)
        self.assertTrue(settings and followup and general, "Missing follow-up configuration menus")
        self.assertEqual(settings.name, "Configuración")
        self.assertEqual(followup.name, "Seguimiento automático")
        self.assertEqual(settings.parent_id, root)
        self.assertEqual(followup.parent_id, settings)
        self.assertEqual(general.parent_id, followup)
        repair = self.env.ref("mc_rov.menu_repair_activity_policy")
        self.assertEqual(repair.parent_id, followup)
        self.assertEqual(repair.action, self.env.ref("mc_rov.action_repair_activity_policy"))
        group_field = "group_ids" if "group_ids" in general._fields else "groups_id"
        coordinator_group = self.env.ref("mc_rov.group_work_assignment_coordinate")
        for menu in (settings, followup, general, repair):
            self.assertIn(coordinator_group, menu[group_field])

    def test_pause_is_recorded_in_native_chatter(self):
        row = self._control()
        coordinator = self._coordinator()
        self.env.flush_all()
        self.cr.precommit.run()
        before = row.message_ids
        row.with_user(coordinator).write({"enabled": False})
        self.env.flush_all()
        self.cr.precommit.run()
        messages = row.message_ids - before
        self.assertTrue(messages.filtered("tracking_value_ids"))
        self.assertIn(coordinator.partner_id, messages.author_id)

    def test_general_pause_does_not_prevent_repair_order_confirmation(self):
        self._control(enabled=False)
        self._policy()
        order = self._order()
        order.write({"state": "confirmed"})
        self.assertEqual(order.state, "confirmed")
        self.assertFalse(self._runs(order))

    def test_pause_still_allows_exact_revision_to_finish_existing_diagnosis(self):
        self._control()
        _policy, _order, diagnosis, repair = self._visit()
        self._control(enabled=False)
        self._confirm(diagnosis.revision_id)
        self.assertEqual(diagnosis.outcome, "business_done")
        self.assertEqual(repair.outcome, "pending")

    def test_resume_does_not_backfill_skipped_diagnosis(self):
        self._control(enabled=False)
        self._policy()
        order = self._order()
        order.write({"state": "confirmed"})
        self.assertFalse(self._runs(order))
        self._control(enabled=True)
        order.write({"name": "QA seguimiento reactivado"})
        self.assertFalse(self._runs(order))
        order.action_repair_start()
        self.assertEqual(self._runs(order).mapped("stage"), ["repair"])
