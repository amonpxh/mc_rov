"""Read-only KPI contracts over native, immutable final repair attempts."""

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from . import test_repair_acceptance_history as acceptance
from .test_mc_rov_revision import RevisionCommon


class MissingRepairFirstPassKPI(AssertionError):
    """Separate absent adapter assertions from native fixture errors."""


@tagged("post_install", "-at_install", "repair_first_pass_kpi")
class TestRepairFirstPassKPI(RevisionCommon):
    """One selected repair episode cannot hide its first real failure."""

    # A single native fixture covers the adapter's complete permission/result matrix.
    # pylint: disable=too-many-public-methods

    _feature = acceptance.TestRepairAcceptanceHistory._feature
    _native_revision = acceptance.TestRepairAcceptanceHistory._native_revision
    _final = acceptance.TestRepairAcceptanceHistory._final
    _history = acceptance.TestRepairAcceptanceHistory._history
    _operator = acceptance.TestRepairAcceptanceBoundaries._operator
    _deny_source = acceptance.TestRepairAcceptanceBoundaries._deny_source

    def setUp(self):
        super().setUp()
        self._kpi_user = None

    def _kpi(self, user=None):
        if "mc.rov.repair.acceptance.kpi" not in self.env.registry.models:
            raise MissingRepairFirstPassKPI("Missing repair first-pass KPI adapter")
        if user is None:
            if self._kpi_user is None:
                self._kpi_user = self._operator()
            user = self._kpi_user
        return self.env["mc.rov.repair.acceptance.kpi"].with_user(user)

    def _report(self, service, revision):
        return service.get_summary([revision.repair_id.id])

    def _status(self, service, revision):
        return self._report(service, revision)["episodes"][0]["status"]

    def _confirmed(self, **values):
        revision = self._final()
        revision.write(values)
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        return revision

    def test_native_diagnostic_has_no_attempt(self):
        revision = self._native_revision()
        revision.mc_acceptance_purpose = "diagnostic"
        revision.action_confirmar()
        self.assertFalse(self._history(revision))

    def test_native_confirmation_seals_original_flags(self):
        revision = self._confirmed()
        self.assertEqual(self._history(revision).correction_snapshot, "no")
        self.assertEqual(self._history(revision).verdict_snapshot, "aprobado")

    def test_native_abort_preserves_failure(self):
        revision = self._final(False)
        revision.action_start_final_acceptance()
        revision.chequeo_ids[0].resultado = "no_ok"
        revision.action_abort_final_acceptance("Fallo QA antes de terminar")
        self.assertEqual(self._history(revision).verdict_snapshot, "rechazado")

    def test_native_reopen_does_not_replace_history(self):
        revision = self._confirmed()
        attempt = self._history(revision)
        revision.action_volver_a_borrador()
        self.assertEqual(self._history(revision), attempt)
        self.assertEqual(attempt.state, "confirmed")

    def test_empty_selection_has_no_denominator(self):
        report = self._kpi().get_summary([])
        self.assertEqual(report["population"], 0)
        self.assertEqual(report["evaluated"], 0)
        self.assertIsNone(report["value"])
        self.assertEqual(report["episodes"], [])

    def test_approved_first_attempt_passes(self):
        service = self._kpi()
        self.assertEqual(self._status(service, self._confirmed()), "passed")

    def test_informative_observation_can_pass(self):
        service = self._kpi()
        revision = self._final()
        self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
                "severidad": "informativo",
            }
        )
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        self.assertEqual(revision.resultado, "aprobado_con_observaciones")
        self.assertEqual(self._status(service, revision), "passed")

    def test_rejected_confirmed_attempt_fails(self):
        service = self._kpi()
        revision = self._final()
        revision.chequeo_ids[0].resultado = "no_ok"
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        self.assertEqual(self._status(service, revision), "failed")

    def test_real_failure_before_completion_fails(self):
        service = self._kpi()
        revision = self._final(False)
        revision.action_start_final_acceptance()
        revision.chequeo_ids[0].resultado = "no_ok"
        revision.action_abort_final_acceptance("Fallo QA con protocolo incompleto")
        self.assertEqual(self._status(service, revision), "failed")

    def test_later_approval_does_not_erase_first_failure(self):
        service = self._kpi()
        revision = self._final()
        revision.action_start_final_acceptance()
        revision.chequeo_ids[0].resultado = "no_ok"
        revision.action_abort_final_acceptance("Fallo QA inicial")
        self._responder_todo(revision)
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        self.assertEqual(self._status(service, revision), "failed")

    def test_reopening_does_not_remove_original_approval(self):
        service = self._kpi()
        revision = self._confirmed()
        revision.action_volver_a_borrador()
        revision.chequeo_ids[0].resultado = "no_ok"
        self.assertEqual(self._status(service, revision), "passed")

    def test_pending_first_attempt_is_pending(self):
        service = self._kpi()
        revision = self._final()
        revision.action_start_final_acceptance()
        self.assertEqual(self._status(service, revision), "pending")

    def test_live_answers_do_not_seal_pending_attempt(self):
        service = self._kpi()
        revision = self._final()
        revision.action_start_final_acceptance()
        revision.chequeo_ids[0].resultado = "no_ok"
        self.assertEqual(self._status(service, revision), "pending")

    def test_unknown_correction_prevents_first_pass(self):
        service = self._kpi()
        revision = self._confirmed(mc_correction_required="unknown")
        self.assertEqual(self._status(service, revision), "unknown")

    def test_unknown_retest_prevents_first_pass(self):
        service = self._kpi()
        revision = self._confirmed(mc_retest_required="unknown")
        self.assertEqual(self._status(service, revision), "unknown")

    def test_correction_requirement_fails(self):
        service = self._kpi()
        revision = self._confirmed(mc_correction_required="yes")
        self.assertEqual(self._status(service, revision), "failed")

    def test_retest_requirement_fails(self):
        service = self._kpi()
        revision = self._confirmed(mc_retest_required="yes")
        self.assertEqual(self._status(service, revision), "failed")

    def test_diagnostic_confirmation_is_not_final_success(self):
        service = self._kpi()
        revision = self._native_revision()
        revision.mc_acceptance_purpose = "diagnostic"
        revision.action_confirmar()
        self.assertEqual(self._status(service, revision), "unknown")

    def test_unclassified_legacy_confirmation_is_unknown(self):
        service = self._kpi()
        revision = self._native_revision()
        revision.action_confirmar()
        self.assertEqual(self._status(service, revision), "unknown")

    def test_multiple_revisions_still_use_episode_first_attempt(self):
        service = self._kpi()
        first = self._final()
        first.action_start_final_acceptance()
        first.chequeo_ids[0].resultado = "no_ok"
        first.action_abort_final_acceptance("Fallo QA en revisión anterior")
        second = self._revision(tipo="reparacion", repair_id=first.repair_id.id, motivo="otro")
        second.write(
            {
                "mc_acceptance_purpose": "final",
                "mc_correction_required": "no",
                "mc_retest_required": "no",
            }
        )
        self._corrida_completa(second)
        self._responder_todo(second)
        self._responder_sellos(second)
        second.action_start_final_acceptance()
        second.action_confirmar()
        self.assertEqual(self._status(service, second), "failed")

    def test_duplicate_selection_does_not_inflate_population(self):
        service = self._kpi()
        revision = self._confirmed()
        report = service.get_summary([revision.repair_id.id] * 3)
        self.assertEqual(report["population"], 1)
        self.assertEqual(report["passed"], 1)

    def test_coverage_distinguishes_pending_and_missing(self):
        service = self._kpi()
        passed = self._confirmed()
        failed = self._confirmed(mc_correction_required="yes")
        pending = self._final()
        pending.action_start_final_acceptance()
        unknown = self._native_revision()
        report = service.get_summary([r.repair_id.id for r in (passed, failed, pending, unknown)])
        self.assertEqual(
            [
                report[k]
                for k in ("population", "passed", "failed", "pending", "unknown", "evaluated")
            ],
            [4, 1, 1, 1, 1, 2],
        )
        self.assertEqual(report["value"], 50)
        self.assertEqual(report["coverage_percent"], 50)
        self.assertEqual(report["basis"], "selected_repairs_current")

    def test_summary_never_returns_private_snapshots(self):
        service = self._kpi()
        report = self._report(service, self._confirmed())
        self.assertEqual(
            set(report["episodes"][0]), {"repair_id", "lot_id", "status", "first_ordinal"}
        )

    def test_summary_is_readonly(self):
        service = self._kpi()
        revision = self._confirmed()
        self.env.flush_all()
        self.env.cr.precommit.run()

        def stored_snapshot():
            # Compare persisted evidence without computing unrelated restricted HTML.
            rows = []
            for table, identity in (
                ("mc_rov_revision", revision.id),
                ("mc_rov_repair_acceptance_attempt", self._history(revision).id),
                ("repair_order", revision.repair_id.id),
            ):
                self.env.cr.execute(f"SELECT to_jsonb(t) FROM {table} t WHERE id=%s", [identity])
                rows.append(self.env.cr.fetchone()[0])
            return rows

        before = stored_snapshot()
        self._report(service, revision)
        self.env.flush_all()
        self.assertEqual(stored_snapshot(), before)

    def test_internal_without_team_is_denied(self):
        self._kpi()
        user = new_test_user(
            self.env,
            login="qa_first_pass_without_team",
            groups="base.group_user,stock.group_stock_user",
        )
        with self.assertRaises(AccessError):
            self._kpi(user).get_summary([])

    def test_portal_is_denied_even_empty(self):
        self._kpi()
        portal = new_test_user(self.env, login="qa_first_pass_portal", groups="base.group_portal")
        with self.assertRaises(AccessError):
            self._kpi(portal).get_summary([])

    def test_restricted_repair_denies_whole_selection(self):
        service = self._kpi()
        revision = self._confirmed()
        self._deny_source("repair.order", revision.repair_id)
        with self.assertRaises(AccessError):
            self._report(service, revision)

    def test_restricted_historical_revision_denies_episode(self):
        service = self._kpi()
        revision = self._confirmed()
        self._deny_source("mc.rov.revision", revision)
        with self.assertRaises(AccessError):
            self._report(service, revision)

    def test_restricted_serial_is_denied(self):
        service = self._kpi()
        revision = self._confirmed()
        self._deny_source("stock.lot", revision.lot_id)
        with self.assertRaises(AccessError):
            self._report(service, revision)

    def test_restricted_product_is_denied(self):
        service = self._kpi()
        revision = self._confirmed()
        self._deny_source("product.product", revision.product_id)
        with self.assertRaises(AccessError):
            self._report(service, revision)

    def test_selected_company_cannot_expose_other_company(self):
        service = self._kpi()
        revision = self._confirmed()
        company = self.env["res.company"].create({"name": "QA KPI empresa alternativa"})
        service.env.user.with_env(self.env).write({"company_ids": [Command.link(company.id)]})
        with self.assertRaises(AccessError):
            self._report(service.with_context(allowed_company_ids=[company.id]), revision)

    def test_forged_company_context_is_rejected(self):
        service = self._kpi()
        company = self.env["res.company"].create({"name": "QA KPI empresa no autorizada"})
        with self.assertRaises(AccessError):
            service.with_context(allowed_company_ids=[company.id]).get_summary([])

    def test_invalid_ids_are_rejected(self):
        service = self._kpi()
        for value in (False, "1", [True], [0], [-1], [1.0], ["1"]):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                service.get_summary(value)

    def test_missing_source_is_not_silently_omitted(self):
        service = self._kpi()
        with self.assertRaises(AccessError):
            service.get_summary([2147483647])
