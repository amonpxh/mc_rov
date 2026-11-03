"""KPI por documento autorizado: no convertir acceso privado en acceso público."""

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user

from . import test_automatic_activity_completion as completion
from .acceptance_activity_common import AcceptanceActivityCommon
from .engineering_activity_common import EngineeringActivityCommon
from .inventory_activity_common import InventoryActivityCommon
from .manufacturing_activity_common import ManufacturingActivityCommon
from .quality_activity_common import QualityActivityCommon
from .test_mc_rov_revision import RevisionCommon


class WorkKPIChecks(TransactionCase):
    """Helpers only: no inherited tests and no replacement of native events."""

    _completion_control = completion.AutomaticCompletionChecks._completion_control
    _assert_open_fixture = completion.AutomaticCompletionChecks._assert_open_fixture

    def _service(self, user=None):
        self.assertTrue(
            "mc.rov.work.kpi" in self.env.registry.models,
            "Missing work KPI service",
        )
        return self.env["mc.rov.work.kpi"].with_user(user or self.env.user)

    def _team(self, user):
        user.with_env(self.env).write(
            {"group_ids": [Command.link(self.env.ref("mc_rov.group_work_assignment_team").id)]}
        )
        return user

    def _metrics(self, service, process=None, **values):
        report = service.get_summary(process=process or self.process, **values)
        row = next(
            item for item in report["processes"] if item["key"] == (process or self.process)
        )
        self.assertTrue(row["available"])
        return row["metrics"]

    def _assert_pending_delta(self):
        service = self._service(self._team(self.env.user))
        before = self._metrics(service)["pending"]
        self._assert_open_fixture()
        self.assertEqual(self._metrics(service)["pending"] - before, self.pending_delta)

    def _assert_readonly(self):
        self._service()
        source, run, activity = self._assert_open_fixture()
        service = self._service(self._team(activity.user_id))
        self.env.flush_all()
        self.env.cr.precommit.run()
        names = [name for name in ("state", "stage_id", "estado") if name in source._fields]
        before = (
            source.read(names or ["id"]),
            run.read(),
            activity.read(["active", "date_deadline"]),
        )
        self._metrics(service)
        self.env.flush_all()
        self.assertEqual(
            (source.read(names or ["id"]), run.read(), activity.read(["active", "date_deadline"])),
            before,
        )


@tagged("post_install", "-at_install", "work_kpi")
class TestRepairWorkKPI(WorkKPIChecks, RevisionCommon):
    """Native repair events and read-only KPI contract."""

    process = "repair"
    pending_delta = 1
    _completion_fixture = completion.TestRepairAutomaticCompletion._completion_fixture
    _policy = completion.TestRepairAutomaticCompletion._policy
    _order = completion.TestRepairAutomaticCompletion._order
    _runs = completion.TestRepairAutomaticCompletion._runs

    def test_native_fixture_control(self):
        self._assert_open_fixture()

    def test_pending_is_counted_once_per_event(self):
        self._assert_pending_delta()

    def test_summary_does_not_write_business_or_private_history(self):
        self._assert_readonly()


@tagged("post_install", "-at_install", "work_kpi")
class TestManufacturingWorkKPI(WorkKPIChecks, ManufacturingActivityCommon):
    """Native manufacturing events and read-only KPI contract."""

    process = "manufacturing"
    pending_delta = 1
    _completion_fixture = completion.TestManufacturingAutomaticCompletion._completion_fixture

    def test_native_fixture_control(self):
        self._assert_open_fixture()

    def test_pending_is_counted_once_per_event(self):
        self._assert_pending_delta()

    def test_summary_does_not_write_business_or_private_history(self):
        self._assert_readonly()


@tagged("post_install", "-at_install", "work_kpi")
class TestAcceptanceWorkKPI(WorkKPIChecks, AcceptanceActivityCommon):
    """Native acceptance events and read-only KPI contract."""

    process = "acceptance"
    pending_delta = 2
    _completion_fixture = completion.TestAcceptanceAutomaticCompletion._completion_fixture

    def test_native_fixture_control(self):
        self._assert_open_fixture()

    def test_pending_is_counted_once_per_event(self):
        self._assert_pending_delta()

    def test_summary_does_not_write_business_or_private_history(self):
        self._assert_readonly()


@tagged("post_install", "-at_install", "work_kpi")
class TestQualityWorkKPI(WorkKPIChecks, QualityActivityCommon):
    """Native quality events and read-only KPI contract."""

    process = "quality"
    pending_delta = 1
    _completion_fixture = completion.TestQualityAutomaticCompletion._completion_fixture

    def test_native_fixture_control(self):
        self._assert_open_fixture()

    def test_pending_is_counted_once_per_event(self):
        self._assert_pending_delta()

    def test_summary_does_not_write_business_or_private_history(self):
        self._assert_readonly()


@tagged("post_install", "-at_install", "work_kpi")
class TestEngineeringWorkKPI(WorkKPIChecks, EngineeringActivityCommon):
    """Native engineering events and read-only KPI contract."""

    process = "engineering"
    pending_delta = 1
    _completion_fixture = completion.TestEngineeringAutomaticCompletion._completion_fixture

    def test_native_fixture_control(self):
        self._assert_open_fixture()

    def test_pending_is_counted_once_per_event(self):
        self._assert_pending_delta()

    def test_summary_does_not_write_business_or_private_history(self):
        self._assert_readonly()


@tagged("post_install", "-at_install", "work_kpi")
class TestInventoryWorkKPI(WorkKPIChecks, InventoryActivityCommon):
    """Native inventory events and read-only KPI contract."""

    process = "inventory"
    pending_delta = 1
    _completion_fixture = completion.TestInventoryAutomaticCompletion._completion_fixture

    def test_native_fixture_control(self):
        self._assert_open_fixture()

    def test_pending_is_counted_once_per_event(self):
        self._assert_pending_delta()

    def test_summary_does_not_write_business_or_private_history(self):
        self._assert_readonly()


@tagged("post_install", "-at_install", "work_kpi")
class TestWorkKPIAccess(WorkKPIChecks, InventoryActivityCommon):
    """Team capability is separate from coordination and source model access."""

    process = "inventory"
    _completion_fixture = completion.TestInventoryAutomaticCompletion._completion_fixture

    def _own(self):
        self._service()
        source, run, activity = self._assert_open_fixture()
        return source, run, self._service(self._team(activity.user_id))

    def _finish(self, source):
        source.move_ids.with_user(self.operator).write({"quantity": 2, "picked": True})
        self.assertIs(source.with_user(self.operator).button_validate(), True)

    def _source_rule(self, domain, **values):
        return self.env["ir.rule"].create(
            {
                "name": "QA KPI source boundary",
                "model_id": self.env["ir.model"]._get_id("stock.picking"),
                "domain_force": domain,
                **values,
            }
        )

    def test_operator_without_team_cannot_query(self):
        service = self._service(self.operator)
        with self.assertRaises(AccessError):
            service.get_summary(process="inventory")

    def test_coordination_does_not_imply_team_query(self):
        service = self._service(self.coordinator)
        self.assertFalse(self.coordinator.has_group("mc_rov.group_work_assignment_team"))
        with self.assertRaises(AccessError):
            service.get_summary(process="inventory")

    def test_portal_cannot_query(self):
        self._service()
        portal = new_test_user(self.env, login="qa_kpi_portal", groups="base.group_portal")
        with self.assertRaises(AccessError):
            self._service(portal).get_summary()

    def test_invalid_process_is_rejected(self):
        service = self._service(self._team(self.operator))
        with self.assertRaises(ValidationError):
            service.get_summary(process="__all_private__")

    def test_invalid_date_is_rejected(self):
        service = self._service(self._team(self.operator))
        with self.assertRaises(ValidationError):
            service.get_summary(date_from="2026-02-30")

    def test_boolean_true_is_not_a_date(self):
        service = self._service(self._team(self.operator))
        with self.assertRaises(ValidationError):
            service.get_summary(date_from=True)

    def test_reversed_period_is_rejected(self):
        service = self._service(self._team(self.operator))
        with self.assertRaises(ValidationError):
            service.get_summary(date_from="2026-11-03", date_to="2026-11-02")

    def test_foreign_allowed_company_context_is_rejected(self):
        service = self._service(self._team(self.operator))
        other = self._other_company()
        self.assertNotIn(other, self.operator.company_ids)
        with self.assertRaises(AccessError):
            service.with_context(allowed_company_ids=[other.id]).get_summary()

    def test_hidden_source_does_not_contribute(self):
        source, _run, service = self._own()
        before = self._metrics(service)["pending"]
        self._source_rule(repr([("id", "!=", source.id)]))
        self.assertEqual(self._metrics(service)["pending"], before - 1)

    def test_readonly_source_does_not_require_write_gateway(self):
        source, _run, service = self._own()
        self._source_rule(
            "[('id', '=', 0)]",
            perm_read=False,
            perm_write=True,
            perm_create=False,
            perm_unlink=False,
        )
        self.assertTrue(source.with_user(self.operator).has_access("read"))
        self.assertFalse(source.with_user(self.operator).has_access("write"))
        self.assertGreaterEqual(self._metrics(service)["pending"], 1)

    def test_summary_does_not_grant_private_history_acl(self):
        _source, run, service = self._own()
        self._metrics(service)
        with self.assertRaises(AccessError):
            run.with_user(self.operator).read(["outcome"])

    def test_response_contains_no_individual_identifiers(self):
        _source, _run, service = self._own()
        report = service.get_summary(process="inventory")

        def check(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    self.assertFalse(key == "id" or key.endswith("_id") or key.endswith("_ids"))
                    check(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    check(item)

        check(report)

    def test_period_does_not_hide_current_backlog(self):
        _source, _run, service = self._own()
        self.assertEqual(
            self._metrics(service, date_from="2000-01-01", date_to="2000-01-02")["pending"],
            self._metrics(service)["pending"],
        )

    def test_real_validation_increments_completion(self):
        source, _run, service = self._own()
        before = self._metrics(service)["completed"]
        self._finish(source)
        self.assertEqual(self._metrics(service)["completed"], before + 1)

    def test_cancellation_is_not_completion(self):
        source, _run, service = self._own()
        before = self._metrics(service)
        source.with_user(self.operator).action_cancel()
        after = self._metrics(service)
        self.assertEqual(after["completed"], before["completed"])
        self.assertEqual(after["cancelled"], before["cancelled"] + 1)

    def test_missing_final_deadline_has_unknown_coverage(self):
        source, run, service = self._own()
        self._finish(source)
        run.write({"current_deadline": False})
        before = self._metrics(service)["current_compliance"]["unknown"]
        run.current_deadline = run.original_deadline
        self.assertEqual(self._metrics(service)["current_compliance"]["unknown"], before - 1)

    def test_manual_history_is_not_real_completion(self):
        source, run, service = self._own()
        self._finish(source)
        before = self._metrics(service)
        run.write({"outcome": "manual_done"})
        after = self._metrics(service)
        self.assertEqual(after["completed"], before["completed"] - 1)
        self.assertEqual(after["manual_history"], before["manual_history"] + 1)

    def test_unavailable_flow_is_not_zero(self):
        self._service()
        user = self._team(self.outsider)
        service = self._service(user)
        row = next(
            item for item in service.get_summary()["processes"] if item["key"] == "inventory"
        )
        self.assertFalse(row["available"])
        self.assertIsNone(row["metrics"])
        with self.assertRaises(AccessError):
            service.get_summary(process="inventory")
