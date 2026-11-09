"""Formal joint acceptance must start before either independent technical result."""

import copy

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .acceptance_activity_common import AcceptanceActivityCommon


class MissingNewAcceptanceStart(AssertionError):
    """Expected missing formal-start assertions, distinct from native fixture errors."""


@tagged("post_install", "-at_install", "new_acceptance_start")
class TestNewAcceptanceStart(AcceptanceActivityCommon):
    """Explicit manufactured unit and two draft sources, even with reminders off."""

    # One native fixture exercises the complete source/role/identity matrix.
    # pylint: disable=too-many-public-methods

    def _service(self, user=None):
        if not {
            "mc.rov.new.acceptance",
            "mc.rov.new.acceptance.episode",
            "mc.rov.new.acceptance.attempt",
        } <= set(self.env.registry.models):
            raise MissingNewAcceptanceStart("Missing new-unit formal acceptance start")
        return self.env["mc.rov.new.acceptance"].with_user(user or self.env.user)

    def _pause(self):
        control = self.env["mc.rov.automation.control"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        if control:
            control.enabled = False
        else:
            self.env["mc.rov.automation.control"].create(
                {"company_id": self.env.company.id, "enabled": False}
            )

    def _unit(self):
        self._pause()
        production = self._finished_production()
        lot = self.env["mc.rov.acceptance.activity.automation"]._produced_lots(production)
        self.assertEqual(len(lot), 1)
        rnd = self._revision(lot_id=lot.id, tipo="rendimiento")
        trn = self._revision(lot_id=lot.id, tipo="terreno")
        return production, lot, rnd, trn

    def _start(self, service, unit):
        return service.start_attempt(*(record.id for record in unit))

    def _attempts(self, lot):
        return (
            self.env["mc.rov.new.acceptance.attempt"]
            .sudo()
            .search([("episode_id.lot_id", "=", lot.id)], order="ordinal")
        )

    def _operator(self, portal=False):
        groups = (
            "base.group_portal"
            if portal
            else "base.group_user,stock.group_stock_user,mrp.group_mrp_user"
        )
        return new_test_user(self.env, login="qa_new_acceptance_start", groups=groups)

    def _deny(self, record):
        self.env["ir.rule"].create(
            {
                "name": "QA new acceptance source denial",
                "model_id": self.env["ir.model"]._get_id(record._name),
                "domain_force": f"[('id', '!=', {record.id})]",
            }
        )

    def test_native_finished_unit_has_positive_serial_output(self):
        production, lot, _rnd, _trn = self._unit()
        self.assertEqual(production.state, "done")
        self.assertEqual(
            self.env["mc.rov.acceptance.activity.automation"]._produced_lots(production), lot
        )

    def test_native_split_preserves_production_group(self):
        self._pause()
        production = self._production(product_qty=2)
        production.action_confirm()
        group = production.production_group_id
        parts = production._split_productions(amounts={production: [1, 1]})
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts.production_group_id, group)

    def test_native_paused_reminders_create_no_cycle(self):
        _production, lot, _rnd, _trn = self._unit()
        self.assertFalse(
            self.env["mc.rov.acceptance.activity.cycle"].search([("lot_id", "=", lot.id)])
        )

    def test_native_sources_are_independent_draft_types(self):
        _production, _lot, rnd, trn = self._unit()
        self.assertEqual((rnd.tipo, trn.tipo), ("rendimiento", "terreno"))
        self.assertEqual(set((rnd | trn).mapped("estado")), {"borrador"})

    def test_start_works_with_all_reminders_paused(self):
        service = self._service()
        unit = self._unit()
        self._start(service, unit)
        self.assertEqual(len(self._attempts(unit[1])), 1)
        self.assertFalse(self._acceptance_activities(unit[1]))

    def test_first_ordinal_is_one_and_pending(self):
        service = self._service()
        unit = self._unit()
        self._start(service, unit)
        self.assertEqual(
            (self._attempts(unit[1]).ordinal, self._attempts(unit[1]).state), (1, "pending")
        )

    def test_both_sources_are_bound_explicitly(self):
        service = self._service()
        unit = self._unit()
        self._start(service, unit)
        attempt = self._attempts(unit[1])
        self.assertEqual((attempt.rnd_id, attempt.trn_id), unit[2:])

    def test_episode_captures_native_manufacturing_identity(self):
        service = self._service()
        unit = self._unit()
        self._start(service, unit)
        episode = self._attempts(unit[1]).episode_id
        self.assertEqual(
            (episode.production_id, episode.lot_id, episode.production_group_id),
            (unit[0], unit[1], unit[0].production_group_id),
        )

    def test_identical_start_is_idempotent(self):
        service = self._service()
        unit = self._unit()
        self._start(service, unit)
        original = self._attempts(unit[1])
        self._start(service, unit)
        self.assertEqual(self._attempts(unit[1]), original)

    def test_pending_attempt_cannot_replace_sources(self):
        service = self._service()
        unit = self._unit()
        self._start(service, unit)
        other = self._revision(lot_id=unit[1].id, tipo="rendimiento")
        with self.assertRaises(UserError):
            self._start(service, (*unit[:2], other, unit[3]))
        self.assertEqual(self._attempts(unit[1]).rnd_id, unit[2])

    def test_distinct_serials_have_distinct_episodes(self):
        service = self._service()
        first, second = self._unit(), self._unit()
        self._start(service, first)
        self._start(service, second)
        self.assertNotEqual(
            self._attempts(first[1]).episode_id, self._attempts(second[1]).episode_id
        )

    def test_draft_production_cannot_start(self):
        service = self._service()
        unit = self._unit()
        draft = self._production()
        with self.assertRaises(UserError):
            self._start(service, (draft, *unit[1:]))

    def test_serial_must_be_actually_produced(self):
        service = self._service()
        first, second = self._unit(), self._unit()
        with self.assertRaises(UserError):
            self._start(service, (first[0], *second[1:]))

    def test_rnd_requires_performance_type(self):
        service = self._service()
        unit = self._unit()
        with self.assertRaises(ValidationError):
            self._start(service, (*unit[:2], unit[3], unit[2]))

    def test_trn_requires_field_type(self):
        service = self._service()
        unit = self._unit()
        with self.assertRaises(ValidationError):
            self._start(service, (*unit[:3], unit[2]))

    def test_rnd_cannot_belong_to_other_serial(self):
        service = self._service()
        first, second = self._unit(), self._unit()
        with self.assertRaises(ValidationError):
            self._start(service, (*first[:2], second[2], first[3]))

    def test_trn_cannot_belong_to_other_serial(self):
        service = self._service()
        first, second = self._unit(), self._unit()
        with self.assertRaises(ValidationError):
            self._start(service, (*first[:3], second[3]))

    def test_repair_revision_cannot_be_selected(self):
        service = self._service()
        unit = self._unit()
        repair = self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "product_qty": 1,
                "product_uom": self.product.uom_id.id,
                "lot_id": unit[1].id,
            }
        )
        unit[2].write({"repair_id": repair.id})
        with self.assertRaises(ValidationError):
            self._start(service, unit)

    def test_already_confirmed_source_cannot_invent_first_attempt(self):
        service = self._service()
        unit = self._unit()
        self._corrida_completa(unit[2])
        self._responder_todo(unit[2])
        self._responder_sellos(unit[2])
        unit[2].action_confirmar()
        with self.assertRaises(UserError):
            self._start(service, unit)

    def test_requirements_survive_later_catalog_rename(self):
        service = self._service()
        unit = self._unit()
        self._start(service, unit)
        attempt = self._attempts(unit[1])
        original = copy.deepcopy(attempt.requirements_snapshot)
        unit[2].chequeo_ids[0].chequeo_id.name = "QA catálogo renombrado"
        self.assertEqual(attempt.requirements_snapshot, original)

    def test_taller_can_start_without_team_query_role(self):
        self._service()
        unit = self._unit()
        self._start(self._service(self._operator()), unit)
        self.assertTrue(self._attempts(unit[1]))

    def test_portal_cannot_start(self):
        self._service()
        unit = self._unit()
        with self.assertRaises(AccessError):
            self._start(self._service(self._operator(portal=True)), unit)

    def test_foreign_active_company_cannot_start(self):
        self._service()
        unit = self._unit()
        user = self._operator()
        company = self.env["res.company"].create({"name": "QA aceptación nueva otra empresa"})
        user.write({"company_ids": [Command.link(company.id)]})
        with self.assertRaises(AccessError):
            self._start(self._service(user).with_context(allowed_company_ids=[company.id]), unit)

    def test_restricted_production_is_denied(self):
        self._service()
        unit = self._unit()
        self._deny(unit[0])
        with self.assertRaises(AccessError):
            self._start(self._service(self._operator()), unit)

    def test_restricted_serial_is_denied(self):
        self._service()
        unit = self._unit()
        self._deny(unit[1])
        with self.assertRaises(AccessError):
            self._start(self._service(self._operator()), unit)

    def test_restricted_revision_is_denied(self):
        self._service()
        unit = self._unit()
        self._deny(unit[3])
        with self.assertRaises(AccessError):
            self._start(self._service(self._operator()), unit)

    def test_private_attempt_has_no_read_acl(self):
        service = self._service()
        unit = self._unit()
        self._start(service, unit)
        with self.assertRaises(AccessError):
            self._attempts(unit[1]).with_user(self._operator()).read(["requirements_snapshot"])

    def test_sudo_cannot_create_attempt_without_internal_capability(self):
        self._service()
        with self.assertRaises(UserError):
            self.env["mc.rov.new.acceptance.attempt"].sudo().create({})

    def test_episode_cannot_be_forged_by_direct_create(self):
        self._service()
        with self.assertRaises(UserError):
            self.env["mc.rov.new.acceptance.episode"].sudo().create({})

    def test_rpc_context_cannot_forge_capture_capability(self):
        self._service()
        with self.assertRaises(UserError):
            self.env["mc.rov.new.acceptance.attempt"].sudo().with_context(
                mc_new_acceptance_capability=True
            ).create({})

    def test_attempt_cannot_be_deleted(self):
        service = self._service()
        unit = self._unit()
        self._start(service, unit)
        with self.assertRaises(UserError):
            self._attempts(unit[1]).unlink()

    def test_pending_source_identity_is_locked(self):
        service = self._service()
        unit = self._unit()
        self._start(service, unit)
        with self.assertRaises(UserError):
            unit[2].write({"tipo": "terreno"})

    def test_pending_source_scope_refresh_is_blocked(self):
        service = self._service()
        unit = self._unit()
        self._start(service, unit)
        with self.assertRaises(UserError):
            unit[3].action_actualizar_checklist()

    def test_invalid_rpc_ids_are_rejected(self):
        service = self._service()
        for value in (False, 0, -1, "1", 1.0):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                service.start_attempt(value, value, value, value)
