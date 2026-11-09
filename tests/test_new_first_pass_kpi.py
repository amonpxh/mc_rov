"""Read first joint acceptance from immutable episodes of actually produced ROV units."""

import copy
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user
from odoo.tools import SQL

from .acceptance_activity_common import AcceptanceActivityCommon
from . import test_new_acceptance_events as events


class MissingNewFirstPassKPI(AssertionError):
    """Expected absence of the new-unit KPI adapter, distinct from fixture errors."""


@tagged("post_install", "-at_install", "new_first_pass_kpi")
class TestNewFirstPassKPI(AcceptanceActivityCommon):
    """Keep first outcomes, unit denominators and complete source authorization intact."""

    # One native fixture covers the source/result matrix, without inheriting test methods.
    # pylint: disable=too-many-public-methods
    _service = events.TestNewAcceptanceEvents._service
    _pause = events.TestNewAcceptanceEvents._pause
    _unit = events.TestNewAcceptanceEvents._unit
    _start = events.TestNewAcceptanceEvents._start
    _attempts = events.TestNewAcceptanceEvents._attempts
    _deny = events.TestNewAcceptanceEvents._deny
    _events = events.TestNewAcceptanceEvents._events
    _complete = events.TestNewAcceptanceEvents._complete
    _started = events.TestNewAcceptanceEvents._started
    _result = events.TestNewAcceptanceEvents._result

    def setUp(self):
        super().setUp()
        self._kpi_user = None

    def _kpi(self, user=None):
        if "mc.rov.new.acceptance.kpi" not in self.env.registry.models:
            raise MissingNewFirstPassKPI("Missing new-unit first-pass KPI adapter")
        if user is None:
            user = getattr(self, "_kpi_user", None)
            if user is None:
                user = new_test_user(
                    self.env,
                    login="qa_new_first_pass_kpi",
                    groups=(
                        "base.group_user,stock.group_stock_user,mrp.group_mrp_user,"
                        "mc_rov.group_work_assignment_team"
                    ),
                )
                self._kpi_user = user
        return self.env["mc.rov.new.acceptance.kpi"].with_user(user)

    def _confirmed(self):
        unit = self._started(self._events())
        (unit[2] | unit[3]).action_confirmar()
        return unit

    def _report(self, service, unit):
        return service.get_summary([unit[0].id])

    def _status(self, service, unit):
        return self._report(service, unit)["episodes"][0]["status"]

    def test_native_joint_success_is_sealed(self):
        unit = self._confirmed()
        self.assertEqual(self._result(unit).first_pass_snapshot, "passed")

    def test_native_joint_failure_is_sealed(self):
        unit = self._started(self._events())
        unit[2].chequeo_ids[0].resultado = "no_ok"
        unit[2].action_confirmar()
        self.assertEqual(self._result(unit).first_pass_snapshot, "failed")

    def test_native_reopen_preserves_joint_history(self):
        unit = self._confirmed()
        before = copy.deepcopy(self._result(unit).requirements_snapshot)
        unit[2].action_volver_a_borrador()
        self.assertEqual(self._result(unit).requirements_snapshot, before)

    def test_native_unselected_protocols_have_no_formal_history(self):
        unit = self._unit()
        self._complete(unit[2] | unit[3])
        (unit[2] | unit[3]).action_confirmar()
        self.assertFalse(self._attempts(unit[1]))

    def test_empty_selection_has_no_denominator(self):
        report = self._kpi().get_summary([])
        self.assertEqual((report["population"], report["evaluated"]), (0, 0))
        self.assertIsNone(report["value"])
        self.assertEqual(report["episodes"], [])

    def test_both_first_passes_count_as_passed(self):
        service = self._kpi()
        self.assertEqual(self._status(service, self._confirmed()), "passed")

    def test_informative_observation_can_pass(self):
        service = self._kpi()
        unit = self._started(self._events())
        self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": unit[2].id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
                "severidad": "informativo",
            }
        )
        (unit[2] | unit[3]).action_confirmar()
        self.assertEqual(self._status(service, unit), "passed")

    def test_one_passed_phase_keeps_episode_pending(self):
        service = self._kpi()
        unit = self._started(self._events())
        unit[2].action_confirmar()
        self.assertEqual(self._status(service, unit), "pending")

    def test_failure_before_peer_confirmation_fails(self):
        service = self._kpi()
        unit = self._started(self._events())
        unit[2].chequeo_ids[0].resultado = "no_ok"
        unit[2].action_confirmar()
        self.assertEqual(self._status(service, unit), "failed")

    def test_real_abort_before_completion_fails(self):
        service = self._kpi()
        unit = self._started(self._events(), complete=False)
        unit[3].chequeo_ids[0].resultado = "no_ok"
        unit[3].action_abort_new_acceptance("QA fallo real temprano")
        self.assertEqual(self._status(service, unit), "failed")

    def test_explicit_correction_requirement_fails(self):
        service = self._kpi()
        unit = self._started(self._events())
        unit[2].mc_correction_required = "yes"
        unit[2].action_confirmar()
        self.assertEqual(self._status(service, unit), "failed")

    def test_later_joint_approval_does_not_erase_first_failure(self):
        service = self._kpi()
        unit = self._started(self._events())
        unit[2].chequeo_ids[0].resultado = "no_ok"
        unit[2].action_confirmar()
        rnd = self._revision(lot_id=unit[1].id, tipo="rendimiento")
        trn = self._revision(lot_id=unit[1].id, tipo="terreno")
        self._complete(rnd | trn)
        self._start(self._service(), (*unit[:2], rnd, trn))
        (rnd | trn).action_confirmar()
        self.assertEqual(self._status(service, unit), "failed")

    def test_unknown_flags_remain_unknown(self):
        service = self._kpi()
        unit = self._started(self._events())
        unit[3].mc_retest_required = "unknown"
        (unit[2] | unit[3]).action_confirmar()
        self.assertEqual(self._status(service, unit), "unknown")
        self.assertIsNone(self._report(service, unit)["value"])

    def test_unstarted_legacy_confirmations_are_unknown(self):
        service = self._kpi()
        unit = self._unit()
        self._complete(unit[2] | unit[3])
        (unit[2] | unit[3]).action_confirmar()
        self.assertEqual(self._status(service, unit), "unknown")

    def test_duplicate_production_selection_does_not_inflate_units(self):
        service = self._kpi()
        unit = self._confirmed()
        report = service.get_summary([unit[0].id] * 3)
        self.assertEqual((report["population"], report["passed"]), (1, 1))

    def test_coverage_distinguishes_evaluated_pending_and_missing(self):
        service = self._kpi()
        passed = self._confirmed()
        failed = self._started(self._events())
        failed[2].chequeo_ids[0].resultado = "no_ok"
        failed[2].action_confirmar()
        pending = self._started(self._events())
        unknown = self._unit()
        report = service.get_summary([unit[0].id for unit in (passed, failed, pending, unknown)])
        self.assertEqual(
            [
                report[key]
                for key in ("population", "passed", "failed", "pending", "unknown", "evaluated")
            ],
            [4, 1, 1, 1, 1, 2],
        )
        self.assertEqual((report["value"], report["coverage_percent"]), (50, 50))
        self.assertEqual(report["basis"], "selected_productions_new_units_current")

    def test_summary_does_not_return_private_snapshots(self):
        service = self._kpi()
        report = self._report(service, self._confirmed())
        self.assertEqual(
            set(report["episodes"][0]),
            {"lot_id", "company_id", "production_group_id", "status", "first_ordinal"},
        )

    def test_summary_is_readonly(self):
        service = self._kpi()
        unit = self._confirmed()
        self.env.flush_all()
        self.env.cr.precommit.run()

        def snapshot():
            rows = []
            for table, identity in (
                ("mrp_production", unit[0].id),
                ("stock_lot", unit[1].id),
                ("mc_rov_revision", unit[2].id),
                ("mc_rov_new_acceptance_attempt", self._result(unit).id),
            ):
                self.env.cr.execute(
                    SQL(
                        "SELECT to_jsonb(t) FROM %s t WHERE id=%s", SQL.identifier(table), identity
                    )
                )
                rows.append(self.env.cr.fetchone()[0])
            return rows

        before = snapshot()
        self._report(service, unit)
        self.env.flush_all()
        self.assertEqual(snapshot(), before)

    def test_internal_without_team_is_denied_even_empty(self):
        self._kpi()
        user = new_test_user(
            self.env,
            login="qa_new_kpi_without_team",
            groups="base.group_user,stock.group_stock_user,mrp.group_mrp_user",
        )
        with self.assertRaises(AccessError):
            self._kpi(user).get_summary([])

    def test_portal_is_denied_even_empty(self):
        self._kpi()
        user = new_test_user(self.env, login="qa_new_kpi_portal", groups="base.group_portal")
        with self.assertRaises(AccessError):
            self._kpi(user).get_summary([])

    def test_denied_production_rejects_selection(self):
        service = self._kpi()
        unit = self._confirmed()
        self._deny(unit[0])
        with self.assertRaises(AccessError):
            self._report(service, unit)

    def test_denied_historical_performance_rejects_episode(self):
        service = self._kpi()
        unit = self._confirmed()
        self._deny(unit[2])
        with self.assertRaises(AccessError):
            self._report(service, unit)

    def test_denied_historical_field_rejects_episode(self):
        service = self._kpi()
        unit = self._confirmed()
        self._deny(unit[3])
        with self.assertRaises(AccessError):
            self._report(service, unit)

    def test_denied_serial_rejects_episode(self):
        service = self._kpi()
        unit = self._confirmed()
        self._deny(unit[1])
        with self.assertRaises(AccessError):
            self._report(service, unit)

    def test_denied_product_rejects_episode(self):
        service = self._kpi()
        unit = self._confirmed()
        self._deny(unit[1].product_id)
        with self.assertRaises(AccessError):
            self._report(service, unit)

    def test_other_active_company_cannot_expose_episode(self):
        service = self._kpi()
        unit = self._confirmed()
        other = self.env["res.company"].create({"name": "QA KPI new other company"})
        service.env.user.with_env(self.env).write({"company_ids": [Command.link(other.id)]})
        with self.assertRaises(AccessError):
            self._report(service.with_context(allowed_company_ids=[other.id]), unit)

    def test_forged_company_context_is_rejected(self):
        service = self._kpi()
        other = self.env["res.company"].create({"name": "QA KPI new unauthorized company"})
        with self.assertRaises(AccessError):
            service.with_context(allowed_company_ids=[other.id]).get_summary([])

    def test_boolean_is_not_a_production_identity(self):
        service = self._kpi()
        with self.assertRaises(ValidationError):
            service.get_summary([True])

    def test_invalid_selection_shape_is_rejected(self):
        service = self._kpi()
        for value in (None, "1", ["1"], [-1]):
            with self.assertRaises(ValidationError):
                service.get_summary(value)

    def test_nonexistent_production_is_denied(self):
        service = self._kpi()
        with self.assertRaises(AccessError):
            service.get_summary([2147483647])

    def test_readonly_production_access_is_sufficient(self):
        service = self._kpi()
        unit = self._confirmed()
        self.env["ir.rule"].create(
            {
                "name": "QA new KPI deny writes only",
                "model_id": self.env["ir.model"]._get_id("mrp.production"),
                "domain_force": '[("id", "=", 0)]',
                "perm_read": False,
                "perm_write": True,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        with self.assertRaises(AccessError):
            unit[0].with_user(service.env.user).check_access("write")
        self.assertEqual(self._status(service, unit), "passed")

    def test_non_rov_outputs_are_not_rov_population(self):
        service = self._kpi()
        unit = self._unit()
        category = self.env["product.category"].create({"name": "QA outside vehicle tree"})
        unit[1].product_id.categ_id = category
        report = self._report(service, unit)
        self.assertEqual(report["population"], 0)
        self.assertIsNone(report["value"])

    def test_missing_vehicle_root_does_not_produce_false_zero(self):
        service = self._kpi()
        unit = self._unit()
        with patch.object(
            type(self.env["stock.lot"]),
            "_get_rov_root_category",
            return_value=self.env["product.category"],
        ):
            with self.assertRaises(ValidationError):
                self._report(service, unit)

    def test_two_positive_serial_outputs_count_two_units(self):
        service = self._kpi()
        self._pause()
        production = self._finished_production(quantity=2)
        report = service.get_summary([production.id])
        self.assertEqual((report["population"], report["unknown"]), (2, 2))
