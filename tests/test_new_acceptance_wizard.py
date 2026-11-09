"""Explicit native manufacturing entry point for already-produced unit acceptance."""

from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .acceptance_activity_common import AcceptanceActivityCommon
from . import test_new_acceptance_events as events


class MissingNewAcceptanceWizard(AssertionError):
    """Distinguish the absent manufacturing dialog from fixture or business errors."""


@tagged("post_install", "-at_install", "new_acceptance_wizard")
class TestNewAcceptanceWizard(AcceptanceActivityCommon):
    """Require explicit source choice and preserve source authorization on submission."""

    _service = events.TestNewAcceptanceEvents._service
    _pause = events.TestNewAcceptanceEvents._pause
    _unit = events.TestNewAcceptanceEvents._unit
    _start = events.TestNewAcceptanceEvents._start
    _attempts = events.TestNewAcceptanceEvents._attempts
    _operator = events.TestNewAcceptanceEvents._operator
    _deny = events.TestNewAcceptanceEvents._deny

    def _wizard_model(self):
        if "mc.rov.new.acceptance.wizard" not in self.env.registry.models or not callable(
            getattr(self.env["mrp.production"], "action_open_new_acceptance", None)
        ):
            raise MissingNewAcceptanceWizard("Missing native joint acceptance dialog")
        return self.env["mc.rov.new.acceptance.wizard"]

    def _wizard(self, unit):
        return self._wizard_model().create(
            {
                "production_id": unit[0].id,
                "lot_id": unit[1].id,
                "rnd_id": unit[2].id,
                "trn_id": unit[3].id,
            }
        )

    def test_native_manufacturing_form_exists(self):
        view = self.env.ref("mrp.mrp_production_form_view")
        self.assertEqual(
            etree.fromstring(
                self.env["mrp.production"]
                .get_view(view_id=view.id, view_type="form")["arch"]
                .encode()
            ).tag,
            "form",
        )

    def test_native_unit_has_real_positive_serial_output(self):
        unit = self._unit()
        self.assertEqual(unit[0].state, "done")
        self.assertEqual(
            self.env["mc.rov.acceptance.activity.automation"]._produced_lots(unit[0]), unit[1]
        )

    def test_manufacturing_action_opens_native_dialog(self):
        self._wizard_model()
        unit = self._unit()
        action = unit[0].action_open_new_acceptance()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["res_model"], "mc.rov.new.acceptance.wizard")
        self.assertEqual(action["context"]["default_production_id"], unit[0].id)

    def test_dialog_is_transient_with_required_sources(self):
        model = self._wizard_model()
        self.assertTrue(model._transient)
        for name in ("production_id", "lot_id", "rnd_id", "trn_id"):
            self.assertTrue(model._fields[name].required, name)
        self.assertTrue(model._fields["production_id"].readonly)

    def test_single_produced_serial_is_prefilled(self):
        self._wizard_model()
        unit = self._unit()
        action = unit[0].action_open_new_acceptance()
        self.assertEqual(action["context"]["default_lot_id"], unit[1].id)

    def test_multiple_produced_units_require_explicit_serial_choice(self):
        self._wizard_model()
        self._pause()
        production = self._finished_production(quantity=2)
        action = production.action_open_new_acceptance()
        self.assertFalse(action["context"].get("default_lot_id"))

    def test_unfinished_production_cannot_open_formal_dialog(self):
        self._wizard_model()
        with self.assertRaises(UserError):
            self._production().action_open_new_acceptance()

    def test_submit_starts_one_pending_attempt(self):
        self._wizard_model()
        unit = self._unit()
        self._wizard(unit).action_start()
        self.assertEqual(len(self._attempts(unit[1])), 1)
        self.assertEqual(self._attempts(unit[1]).state, "pending")

    def test_submit_opens_performance_without_confirming_protocols(self):
        self._wizard_model()
        unit = self._unit()
        action = self._wizard(unit).action_start()
        self.assertEqual(action["res_model"], "mc.rov.revision")
        self.assertEqual(action["res_id"], unit[2].id)
        self.assertEqual((unit[2].estado, unit[3].estado), ("borrador", "borrador"))

    def test_repeated_submit_is_idempotent(self):
        self._wizard_model()
        unit = self._unit()
        wizard = self._wizard(unit)
        wizard.action_start()
        wizard.action_start()
        self.assertEqual(len(self._attempts(unit[1])), 1)

    def test_submit_rejects_other_produced_serial(self):
        self._wizard_model()
        unit = self._unit()
        other = self._unit()
        wizard = self._wizard(unit)
        wizard.lot_id = other[1]
        with self.assertRaises(UserError):
            wizard.action_start()
        self.assertFalse(self._attempts(unit[1]))

    def test_submit_rejects_wrong_protocol_type(self):
        self._wizard_model()
        unit = self._unit()
        wizard = self._wizard(unit)
        wizard.rnd_id = unit[3]
        with self.assertRaises(ValidationError):
            wizard.action_start()

    def test_denied_manufacturing_cannot_open_dialog(self):
        self._wizard_model()
        unit = self._unit()
        self._deny(unit[0])
        with self.assertRaises(AccessError):
            unit[0].with_user(self._operator()).action_open_new_acceptance()

    def test_denied_protocol_cannot_be_submitted(self):
        self._wizard_model()
        unit = self._unit()
        user = self._operator()
        wizard = (
            self._wizard_model()
            .with_user(user)
            .create(
                {
                    "production_id": unit[0].id,
                    "lot_id": unit[1].id,
                    "rnd_id": unit[2].id,
                    "trn_id": unit[3].id,
                }
            )
        )
        self._deny(unit[2])
        with self.assertRaises(AccessError):
            wizard.action_start()
        self.assertFalse(self._attempts(unit[1]))

    def test_portal_cannot_open_dialog(self):
        self._wizard_model()
        unit = self._unit()
        with self.assertRaises(AccessError):
            unit[0].with_user(self._operator(portal=True)).action_open_new_acceptance()

    def test_foreign_company_context_cannot_open_dialog(self):
        self._wizard_model()
        unit = self._unit()
        user = self._operator()
        other = self.env["res.company"].create({"name": "QA wizard other company"})
        user.write({"company_ids": [Command.link(other.id)]})
        with self.assertRaises(AccessError):
            unit[0].with_user(user).with_context(
                allowed_company_ids=[other.id]
            ).action_open_new_acceptance()

    def test_discarding_dialog_does_not_start_acceptance(self):
        self._wizard_model()
        unit = self._unit()
        self._wizard(unit).unlink()
        self.assertFalse(self._attempts(unit[1]))

    def test_views_expose_entry_and_explicit_source_choice(self):
        self._wizard_model()
        view = self.env.ref("mrp.mrp_production_form_view")
        arch = etree.fromstring(
            self.env["mrp.production"].get_view(view_id=view.id, view_type="form")["arch"].encode()
        )
        self.assertTrue(arch.xpath("//button[@name='action_open_new_acceptance'][@type='object']"))
        dialog = self.env.ref("mc_rov.view_mc_rov_new_acceptance_wizard_form")
        form = etree.fromstring(
            self._wizard_model().get_view(view_id=dialog.id, view_type="form")["arch"].encode()
        )
        for name in ("production_id", "lot_id", "rnd_id", "trn_id"):
            self.assertTrue(form.xpath(f"//field[@name='{name}']"))
        self.assertTrue(form.xpath("//button[@name='action_start'][@type='object']"))
