from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.tests import tagged

from .engineering_activity_common import EngineeringActivityCommon


def _advance_native(case, eco):
    eco.action_new_revision()
    eco.with_user(case.prepare_user).approve()
    eco.write({"stage_id": case.apply_stage.id})


def _bom_change(case):
    bom = case.env["mrp.bom"].create(
        {"product_tmpl_id": case.product.product_tmpl_id.id, "product_qty": 1.0}
    )
    return case._eco(type="bom", bom_id=bom.id)  # pylint: disable=protected-access


@tagged("post_install", "-at_install")
class TestEngineeringNativeEventFixtures(EngineeringActivityCommon):
    """Comprueba aplicación y archivo nativos antes de exigir tareas nuevas."""

    def test_native_product_application_finishes_change(self):
        eco = self._eco()
        _advance_native(self, eco)
        eco.action_apply()
        self.assertEqual(eco.state, "done")

    def test_native_bom_revision_replaces_active_bom(self):
        eco = _bom_change(self)
        original = eco.bom_id
        _advance_native(self, eco)
        self.assertTrue(eco.new_bom_id)
        eco.action_apply()
        self.assertEqual(eco.state, "done")
        self.assertTrue(eco.new_bom_id.active)
        self.assertFalse(original.active)

    def test_native_archive_and_unarchive_keep_change(self):
        eco = self._eco()
        eco.action_archive()
        self.assertFalse(eco.active)
        eco.action_unarchive()
        self.assertTrue(eco.active)


@tagged("post_install", "-at_install")
# Cada evento tiene resultado e identidad independientes.
# pylint: disable=too-many-public-methods
class TestEngineeringActivityEvents(EngineeringActivityCommon):
    """Ejercita los eventos nativos; el servicio no se invoca para forzar el resultado."""

    def _policy(self, **values):
        # Los casos positivos no dependen de la pausa conservada de otro piloto.
        model = self.env["mc.rov.automation.control"]
        control = model.search([("company_id", "=", self.env.company.id)], limit=1)
        if control:
            control.enabled = True
        else:
            model.create({"company_id": self.env.company.id, "enabled": True})
        return super()._policy(**values)

    def _service(self):
        self.assertIn(
            "mc.rov.engineering.activity.automation",
            self.env.registry.models,
            "Missing engineering event automation",
        )
        return self.env["mc.rov.engineering.activity.automation"]

    def _open(self):
        self._service()
        policy = self._policy()
        return policy, self._eco()

    def _runs(self, eco):
        return (
            self.env["mc.rov.engineering.activity.run"]
            .sudo()
            .search([("eco_id", "=", eco.id)], order="id")
        )

    def _cycle(self, eco):
        cycle = (
            self.env["mc.rov.engineering.activity.cycle"].sudo().search([("eco_id", "=", eco.id)])
        )
        self.assertEqual(len(cycle), 1)
        return cycle

    def _own_activities(self, eco):
        types = self.env.ref("mc_rov.activity_type_engineering_prepare") | self.env.ref(
            "mc_rov.activity_type_engineering_apply"
        )
        return eco.activity_ids.filtered(lambda activity: activity.activity_type_id in types)

    def _advance(self, eco):
        _advance_native(self, eco)

    def _apply_approval_template(self):
        return self.env["mrp.eco.approval.template"].create(
            {
                "name": "QA Segunda aprobación obligatoria",
                "stage_id": self.apply_stage.id,
                "approval_type": "mandatory",
                "user_ids": [Command.set(self.prepare_user.ids)],
            }
        )

    def test_creation_starts_one_preparation(self):
        policy, eco = self._open()
        runs = self._runs(eco)
        self.assertEqual(len(runs), 1)
        self.assertEqual((runs.stage, runs.outcome), ("prepare", "pending"))
        self.assertEqual(self._own_activities(eco).user_id, self.prepare_user)
        self.assertEqual(runs.original_deadline, policy._deadline(eco.create_date))

    def test_missing_company_policy_creates_no_tracking(self):
        self._service()
        company = self._other_company()
        eco = (
            self.env["mrp.eco"]
            .with_company(company)
            .create(
                {
                    "name": "QA Empresa sin política",
                    "type": "product",
                    "type_id": self.eco_type.id,
                    "product_tmpl_id": self.product.product_tmpl_id.id,
                    "stage_id": self.prepare_stage.id,
                    "company_id": company.id,
                }
            )
        )
        self.assertFalse(self._runs(eco))
        self.assertFalse(self._own_activities(eco))

    def test_disabled_policy_creates_no_tracking(self):
        self._service()
        self._policy(enabled=False)
        self.assertFalse(self._runs(self._eco()))

    def test_general_pause_prevents_new_preparation(self):
        self._service()
        self._policy()
        model = self.env["mc.rov.automation.control"]
        control = model.search([("company_id", "=", self.env.company.id)], limit=1)
        if control:
            control.enabled = False
        else:
            model.create({"company_id": self.env.company.id, "enabled": False})
        self.assertFalse(self._runs(self._eco()))

    def test_non_rov_change_has_no_tracking(self):
        self._service()
        self._policy()
        category = self.env["product.category"].create({"name": "QA Fuera del árbol ROV"})
        product = self.env["product.product"].create(
            {"name": "QA Producto externo", "categ_id": category.id}
        )
        self.assertFalse(self._runs(self._eco(product_tmpl_id=product.product_tmpl_id.id)))

    def test_change_created_done_has_no_pending(self):
        self._service()
        self._policy()
        eco = self._eco(state="done")
        self.assertFalse(self._runs(eco))
        self.assertFalse(self._own_activities(eco))

    def test_change_created_archived_has_no_pending(self):
        self._service()
        self._policy()
        self.assertFalse(self._runs(self._eco(active=False)))

    def test_change_without_company_has_no_tracking(self):
        self._service()
        self._policy()
        self.assertFalse(self._runs(self._eco(company_id=False)))

    def test_incomplete_recipient_does_not_block_native_creation(self):
        self._service()
        self._policy(prepare_user_id=False)
        eco = self._eco()
        self.assertTrue(eco.exists())
        self.assertFalse(self._runs(eco))

    def test_starting_revision_does_not_finish_preparation(self):
        _, eco = self._open()
        eco.action_new_revision()
        self.assertEqual(eco.state, "progress")
        self.assertEqual(len(self._runs(eco)), 1)
        self.assertEqual(self._runs(eco).outcome, "pending")
        self.assertEqual(
            self._own_activities(eco).activity_type_id,
            self.env.ref("mc_rov.activity_type_engineering_prepare"),
        )

    def test_approval_without_applicable_stage_keeps_preparation(self):
        _, eco = self._open()
        eco.with_user(self.prepare_user).approve()
        self.assertFalse(eco.allow_apply_change)
        self.assertEqual(len(self._runs(eco)), 1)
        self.assertEqual(self._runs(eco).stage, "prepare")
        self.assertEqual(self._runs(eco).outcome, "pending")

    def test_applicable_transition_finishes_preparation_and_starts_apply(self):
        _, eco = self._open()
        self._advance(eco)
        runs = self._runs(eco)
        self.assertEqual(len(runs), 2)
        self.assertEqual((runs[0].stage, runs[0].outcome), ("prepare", "business_done"))
        self.assertEqual((runs[1].stage, runs[1].outcome), ("apply", "pending"))
        self.assertEqual(self._own_activities(eco).user_id, self.apply_user)

    def test_repeating_same_stage_does_not_duplicate_apply(self):
        _, eco = self._open()
        self._advance(eco)
        eco.write({"stage_id": self.apply_stage.id})
        eco.write({"name": "QA Edición ordinaria"})
        self.assertEqual(len(self._runs(eco)), 2)
        self.assertEqual(len(self._own_activities(eco)), 1)

    def test_stage_flag_alone_does_not_bypass_required_approval(self):
        self._service()
        self._apply_approval_template()
        _, eco = self._open()
        self._advance(eco)
        self.assertTrue(eco.allow_apply_change)
        self.assertFalse(eco.allow_change_stage)
        self.assertFalse(self._runs(eco).filtered(lambda run: run.stage == "apply"))
        self.assertEqual(self._runs(eco).outcome, "pending")

    def test_required_approval_in_applicable_stage_starts_apply_after_approve(self):
        self._service()
        self._apply_approval_template()
        _, eco = self._open()
        self._advance(eco)
        eco.with_user(self.prepare_user).approve()
        self.assertTrue(eco.allow_change_stage)
        self.assertEqual(len(self._runs(eco)), 2)
        self.assertEqual(self._runs(eco)[-1].stage, "apply")
        self.assertEqual(len(self._own_activities(eco)), 1)

    def test_rejection_in_applicable_stage_prevents_apply_pending(self):
        self._service()
        self._apply_approval_template()
        _, eco = self._open()
        self._advance(eco)
        eco.with_user(self.prepare_user).reject()
        self.assertFalse(eco.allow_change_stage)
        self.assertFalse(self._runs(eco).filtered(lambda run: run.stage == "apply"))
        self.assertEqual(self._runs(eco).outcome, "pending")

    def test_native_application_finishes_own_pending(self):
        _, eco = self._open()
        self._advance(eco)
        eco.action_apply()
        self.assertEqual(eco.state, "done")
        self.assertFalse(self._own_activities(eco))
        self.assertTrue(all(run.outcome == "business_done" for run in self._runs(eco)))
        self.assertEqual(self._cycle(eco).state, "done")

    def test_native_bom_application_finishes_own_pending(self):
        self._service()
        self._policy()
        eco = _bom_change(self)
        self._advance(eco)
        eco.action_apply()
        self.assertEqual(eco.state, "done")
        self.assertFalse(self._own_activities(eco))
        self.assertEqual(len(self._runs(eco)), 2)
        self.assertTrue(all(run.outcome == "business_done" for run in self._runs(eco)))

    def test_backwards_stage_withdraws_apply_and_returns_to_preparation(self):
        _, eco = self._open()
        self._advance(eco)
        deadline = self._cycle(eco).current_deadline
        eco.write({"stage_id": self.prepare_stage.id})
        runs = self._runs(eco)
        self.assertEqual(len(runs), 3)
        self.assertEqual((runs[1].stage, runs[1].outcome), ("apply", "withdrawn"))
        self.assertEqual((runs[-1].stage, runs[-1].outcome), ("prepare", "pending"))
        self.assertEqual(self._own_activities(eco).date_deadline, deadline)

    def test_archive_cancels_own_pending(self):
        _, eco = self._open()
        eco.action_archive()
        self.assertFalse(eco.active)
        self.assertFalse(self._own_activities(eco))
        self.assertEqual(self._runs(eco).outcome, "cancelled")
        self.assertEqual(self._cycle(eco).state, "cancel")

    def test_unarchive_keeps_original_year_and_cycle(self):
        _, eco = self._open()
        cycle = self._cycle(eco)
        deadline = cycle.original_deadline
        eco.action_archive()
        eco.action_unarchive()
        self.assertEqual(self._cycle(eco), cycle)
        self.assertEqual(cycle.original_deadline, deadline)
        self.assertEqual(self._own_activities(eco).date_deadline, deadline)
        self.assertEqual(len(self._runs(eco)), 2)

    def test_policy_year_change_does_not_extend_existing_change(self):
        policy, eco = self._open()
        deadline = self._cycle(eco).original_deadline
        policy.lead_years = 2
        self._advance(eco)
        self.assertEqual(self._own_activities(eco).date_deadline, deadline)
        self.assertEqual(self._cycle(eco).lead_years, 1)

    def test_policy_timezone_change_does_not_replace_captured_timezone(self):
        policy, eco = self._open()
        deadline = self._cycle(eco).original_deadline
        policy.tz = "Asia/Tokyo"
        self._advance(eco)
        self.assertEqual(self._cycle(eco).deadline_tz, "America/Santiago")
        self.assertEqual(self._own_activities(eco).date_deadline, deadline)

    def test_later_transition_does_not_restart_year(self):
        policy, eco = self._open()
        deadline = policy._deadline(eco.create_date)
        with patch.object(
            fields.Datetime, "now", return_value=eco.create_date + timedelta(days=180)
        ):
            self._advance(eco)
        self.assertEqual(self._own_activities(eco).date_deadline, deadline)

    def test_pause_still_allows_real_application_to_finish(self):
        policy, eco = self._open()
        self._advance(eco)
        policy.enabled = False
        eco.action_apply()
        self.assertEqual(eco.state, "done")
        self.assertFalse(self._own_activities(eco))
        self.assertEqual(self._runs(eco)[-1].outcome, "business_done")

    def test_pause_does_not_create_apply_stage(self):
        policy, eco = self._open()
        policy.enabled = False
        self._advance(eco)
        self.assertFalse(self._own_activities(eco))
        self.assertEqual(len(self._runs(eco)), 1)
        self.assertEqual(self._runs(eco).outcome, "business_done")

    def test_resume_does_not_backfill_creation_or_started_revision(self):
        self._service()
        policy = self._policy(enabled=False)
        eco = self._eco()
        policy.enabled = True
        eco.write({"name": "QA Reanudación sin reconstrucción"})
        eco.action_new_revision()
        self.assertFalse(self._runs(eco))
        self.assertFalse(self._own_activities(eco))

    def test_future_apply_without_tracked_preparation_uses_creation_date(self):
        self._service()
        policy = self._policy(enabled=False)
        eco = self._eco()
        policy.enabled = True
        self._advance(eco)
        runs = self._runs(eco)
        self.assertEqual(len(runs), 1)
        self.assertEqual((runs.stage, runs.outcome), ("apply", "pending"))
        self.assertEqual(runs.original_deadline, policy._deadline(eco.create_date))

    def test_native_approval_activity_ids_dates_and_users_are_preserved(self):
        _, eco = self._open()
        native = eco.activity_ids.filtered(
            lambda row: row.activity_type_id == self.env.ref("mail.mail_activity_data_todo")
        )
        before = native.read(["date_deadline", "user_id", "summary"])
        self._advance(eco)
        self.assertEqual(native.exists(), native)
        self.assertEqual(native.read(["date_deadline", "user_id", "summary"]), before)
        self.assertEqual(len(self._own_activities(eco)), 1)

    def test_stage_name_does_not_identify_preparation_or_application(self):
        self._service()
        self.prepare_stage.name = "Applied"
        _, eco = self._open()
        self.assertEqual(self._runs(eco).stage, "prepare")

    def test_conflict_or_rebase_state_never_qualifies_for_apply(self):
        self._service()
        self._policy()
        for state in ("conflict", "rebase"):
            with self.subTest(state=state):
                eco = self._eco(stage_id=self.apply_stage.id, state=state)
                self.assertFalse(self._runs(eco).filtered(lambda run: run.stage == "apply"))
                self.assertEqual(self._runs(eco).stage, "prepare")

    def test_batch_creation_has_one_cycle_and_pending_per_eco(self):
        self._service()
        self._policy()
        values = {
            "type": "product",
            "type_id": self.eco_type.id,
            "product_tmpl_id": self.product.product_tmpl_id.id,
            "stage_id": self.prepare_stage.id,
            "company_id": self.env.company.id,
        }
        ecos = self.env["mrp.eco"].create(
            [{**values, "name": "QA Lote A"}, {**values, "name": "QA Lote B"}]
        )
        self.assertEqual(len(ecos), 2)
        for eco in ecos:
            self.assertEqual(len(self._runs(eco)), 1)
            self.assertEqual(len(self._own_activities(eco)), 1)
            self.assertEqual(self._cycle(eco).eco_id, eco)
