import json
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .automatic_completion_assertions import assert_automatic_close_rejected
from .acceptance_activity_common import AcceptanceActivityCommon


@tagged("post_install", "-at_install")
# Contratos independientes de consulta, identidad, registros temporales y resultados derivados.
# pylint: disable=too-many-public-methods
class TestAcceptanceActivityBoundaries(AcceptanceActivityCommon):
    """El Centro consulta actividades nativas sin publicar el historial de aceptación."""

    def _visit(self):
        policy = self._acceptance_policy()
        service = self.env["mc.rov.acceptance.activity.automation"]
        production = self._finished_production()
        lot = service._produced_lots(production)
        cycle = self.env["mc.rov.acceptance.activity.cycle"].search(
            [("production_id", "=", production.id), ("lot_id", "=", lot.id)]
        )
        return service, policy, lot, cycle

    def _proof(self, lot, kind="rendimiento"):
        proof = self._revision(lot_id=lot.id, tipo=kind)
        self._corrida_completa(proof)
        self._responder_todo(proof)
        self._responder_sellos(proof)
        return proof

    def _pair(self, service, lot):
        rnd, trn = self._proof(lot), self._proof(lot, "terreno")
        service._select_evidence(lot, rnd=rnd, trn=trn)
        (rnd | trn).action_confirmar()
        return rnd, trn

    def _stage_runs(self, cycle, stage):
        return self.env["mc.rov.acceptance.activity.run"].search(
            [("cycle_id", "=", cycle.id), ("stage", "=", stage)]
        )

    def _assignment(self, user):
        return self.env["mc.rov.work.assignment"].with_user(user)

    def _ids(self, action, user):
        return self.env[action["res_model"]].with_user(user).search(action["domain"]).ids

    def _hide(self, model, record):
        self.env["ir.rule"].create(
            {
                "name": "QA aceptación: origen restringido",
                "model_id": self.env["ir.model"]._get_id(model),
                "domain_force": repr([("id", "!=", record.id)]),
            }
        )
        self.env.invalidate_all()

    def _finding(self, revision, severity="impide_operar"):
        return self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
                "componente_id": self.env.ref("mc_rov.comp_umbilical").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
                "severidad": severity,
            }
        )

    def _human_deletion_error(self, record):
        # Un bloqueo FK es seguro pero no explica al usuario cómo conservar la evidencia.
        with self.cr.savepoint():
            try:
                record.unlink()
            except (UserError, IntegrityError) as error:
                self.assertIsInstance(error, UserError)
                self.assertRegex(str(error).lower(), "aceptación|seguimiento|historial")
                return
            self.fail("El historial de aceptación requiere conservar este registro")

    def test_acceptance_available_for_activities_only(self):
        _service, policy, _lot, _cycle = self._visit()
        assignment = self._assignment(policy.user_id)
        options = {item["key"]: item for item in assignment.get_processes()}
        self.assertTrue(options["acceptance"]["available"])
        self.assertFalse(options["acceptance"]["hint"])
        for kind in ("tasks", "projects"):
            option = next(
                item for item in assignment.get_processes(kind) if item["key"] == "acceptance"
            )
            self.assertFalse(option["available"])

    def test_acceptance_domain_uses_native_type_and_lot_not_frozen_activity_ids(self):
        _service, policy, _lot, _cycle = self._visit()
        action = self._assignment(policy.user_id).action_activities(process="acceptance")
        domain = action["domain"]
        self.assertTrue(
            any(isinstance(term, (tuple, list)) and term[0] == "res_model" for term in domain)
        )
        self.assertTrue(
            any(
                isinstance(term, (tuple, list)) and term[0] == "activity_type_id"
                for term in domain
            )
        )
        self.assertFalse(
            any(isinstance(term, (tuple, list)) and term[0] == "id" for term in domain)
        )
        self.assertNotIn("cycle_id", json.dumps(action))

    def test_open_action_sees_new_acceptance_stage(self):
        service, policy, lot, cycle = self._visit()
        action = self._assignment(policy.user_id).action_activities(process="acceptance")
        rnd = self._proof(lot)
        service._select_evidence(lot, rnd=rnd)
        rnd.chequeo_ids[:1].resultado = "no_ok"
        rnd.action_confirmar()
        resolution = self._stage_runs(cycle, "rejection_performance").activity_id
        self.assertIn(resolution.id, self._ids(action, policy.user_id))

    def test_manual_lot_activity_does_not_enter_acceptance_filter(self):
        _service, policy, lot, _cycle = self._visit()
        manual = self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("stock.lot"),
                "res_id": lot.id,
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "summary": "Realizar prueba de rendimiento",
                "user_id": policy.user_id.id,
            }
        )
        assignment = self._assignment(policy.user_id)
        ids = self._ids(assignment.action_activities(process="acceptance"), policy.user_id)
        self.assertTrue(set(self._acceptance_activities(lot).ids) <= set(ids))
        self.assertNotIn(manual.id, ids)
        self.assertIn(
            manual.id, self._ids(assignment.action_activities(process="equipment"), policy.user_id)
        )

    def test_process_account_and_public_employee_cross_correctly(self):
        _service, policy, lot, cycle = self._visit()
        activity = self._stage_runs(cycle, "performance").activity_id
        activity.mc_employee_id = self.empleado.id
        action = self._assignment(policy.user_id).action_activities(
            process="acceptance", employee_id=self.empleado.id
        )
        self.assertEqual(self._ids(action, policy.user_id), activity.ids)
        self.assertEqual(activity.res_id, lot.id)
        self.assertFalse(self.env["hr.employee"].with_user(policy.user_id).has_access("read"))

    def test_coordinator_without_team_permission_cannot_query_team(self):
        _service, policy, _lot, _cycle = self._visit()
        policy.user_id.group_ids = [
            Command.link(self.env.ref("mc_rov.group_work_assignment_coordinate").id)
        ]
        assignment = self._assignment(policy.user_id)
        self.assertFalse(assignment.get_capabilities()["can_view_team"])
        with self.assertRaises(AccessError):
            assignment.action_activities(scope="team", process="acceptance")

    def test_hidden_lot_not_exposed_by_search_count_or_groups(self):
        _service, policy, lot, _cycle = self._visit()
        activities = self._acceptance_activities(lot)
        self._hide("stock.lot", lot)
        model = self.env["mail.activity"].with_user(policy.user_id)
        domain = [("id", "in", activities.ids)]
        self.assertFalse(model.search(domain))
        self.assertEqual(model.search_count(domain), 0)
        self.assertFalse(model._read_group(domain, ["user_id"], ["__count"]))

    def test_hidden_source_cannot_be_exported_or_opened(self):
        _service, policy, lot, cycle = self._visit()
        activity = self._stage_runs(cycle, "performance").activity_id
        policy.user_id.group_ids = [Command.link(self.env.ref("base.group_allow_export").id)]
        self._hide("stock.lot", lot)
        with self.assertRaises(AccessError):
            activity.with_user(policy.user_id).export_data(["summary"])
        with self.assertRaises(AccessError):
            self._assignment(policy.user_id).action_open_source(activity.id)

    def test_restricted_employee_name_not_exposed_in_export(self):
        _service, policy, _lot, cycle = self._visit()
        activity = self._stage_runs(cycle, "performance").activity_id
        activity.mc_employee_id = self.empleado.id
        policy.user_id.group_ids = [Command.link(self.env.ref("base.group_allow_export").id)]
        self._hide("hr.employee.public", self.env["hr.employee.public"].browse(self.empleado.id))
        rows = activity.with_user(policy.user_id).export_data(["mc_employee_id"])
        self.assertNotIn(self.empleado.name, str(rows))
        self.assertIn("Sin acceso al nombre", str(rows))

    def test_private_cycle_run_history_not_exportable(self):
        service, policy, lot, cycle = self._visit()
        service._select_evidence(lot, rnd=self._proof(lot))
        for model in (
            "mc.rov.acceptance.activity.cycle",
            "mc.rov.acceptance.activity.run",
            "mc.rov.acceptance.evidence.history",
        ):
            self.assertFalse(self.env[model].with_user(policy.user_id).has_access("read"))
        self.assertTrue(self._stage_runs(cycle, "performance"))

    def test_portal_user_cannot_open_or_select_acceptance(self):
        service, _policy, lot, _cycle = self._visit()
        portal = new_test_user(self.env, login="qa_acceptance_portal", groups="base.group_portal")
        with self.assertRaises(AccessError):
            lot.with_user(portal).action_mc_acceptance_evidence()
        with self.assertRaises(AccessError):
            service.with_user(portal)._select_evidence(lot, rnd=self._proof(lot))

    def test_other_company_origin_cannot_expand_actor_context(self):
        service, policy, _lot, _cycle = self._visit()
        with patch.object(
            type(self.env["res.company"]), "_create_internal_project_task", create=True
        ):
            company = self.env["res.company"].create({"name": "QA aceptación otra compañía"})
        foreign = self.env["stock.lot"].create(
            {
                "name": "QA-ACE-OTRA-EMPRESA",
                "product_id": self.product.id,
                "company_id": company.id,
            }
        )
        user = policy.user_id
        user.company_ids = [Command.link(company.id)]
        with self.assertRaises(AccessError):
            service.with_user(user).with_context(
                allowed_company_ids=[self.env.company.id]
            )._select_evidence(foreign)

    def test_forged_context_cannot_replace_selected_cycle(self):
        service, policy, lot, cycle = self._visit()
        revision = self._proof(lot)
        action = lot.with_user(policy.user_id).action_mc_acceptance_evidence()
        defaults = (
            self.env["mc.rov.acceptance.evidence.wizard"]
            .with_user(policy.user_id)
            .with_context(**action["context"], default_cycle_id=999999, acceptance_cycle_id=999999)
            .default_get(["lot_id", "rnd_id", "trn_id", "summary"])
        )
        self.assertNotIn("cycle_id", defaults)
        service.with_user(policy.user_id).with_context(
            acceptance_cycle_id=999999
        )._select_evidence(lot, rnd=revision)
        self.assertEqual(cycle.rnd_id, revision)

    def test_temporary_lot_reconcile_has_no_persistent_effects(self):
        service, _policy, lot, cycle = self._visit()
        before = self._acceptance_activities(lot).ids
        copy = lot.new({}, origin=lot)
        service._reconcile(copy)
        self.assertEqual(self._acceptance_activities(lot).ids, before)
        self.assertEqual(cycle.state, "open")

    def test_temporary_activity_archive_does_not_cancel_real_run(self):
        _service, _policy, _lot, cycle = self._visit()
        run = self._stage_runs(cycle, "performance")
        copy = run.activity_id.new({}, origin=run.activity_id)
        copy.write({"active": False})
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(run.activity_id.active)

    def test_selected_draft_cannot_change_equipment(self):
        service, _policy, lot, _cycle = self._visit()
        proof = self._proof(lot)
        service._select_evidence(lot, rnd=proof)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            proof.lot_id = self._serials()

    def test_selected_draft_cannot_change_test_type(self):
        service, _policy, lot, _cycle = self._visit()
        proof = self._proof(lot)
        service._select_evidence(lot, rnd=proof)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            proof.tipo = "terreno"

    def test_selected_draft_cannot_become_repair_evidence(self):
        service, _policy, lot, _cycle = self._visit()
        proof = self._proof(lot)
        service._select_evidence(lot, rnd=proof)
        repair = self.env["repair.order"].create({"product_id": self.product.id, "lot_id": lot.id})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            proof.repair_id = repair

    def test_selected_draft_deletion_explains_history(self):
        service, _policy, lot, _cycle = self._visit()
        proof = self._proof(lot)
        service._select_evidence(lot, rnd=proof)
        self._human_deletion_error(proof)

    def test_replaced_draft_remains_protected_by_evidence_history(self):
        service, _policy, lot, _cycle = self._visit()
        old = self._proof(lot)
        service._select_evidence(lot, rnd=old)
        service._select_evidence(lot, rnd=self._proof(lot), reason="Nueva prueba elegida")
        self._human_deletion_error(old)

    def test_private_history_deletion_has_human_explanation(self):
        service, _policy, lot, cycle = self._visit()
        service._select_evidence(lot, rnd=self._proof(lot))
        history = self.env["mc.rov.acceptance.evidence.history"].search(
            [("cycle_id", "=", cycle.id)]
        )
        self._human_deletion_error(history)

    def test_followed_activity_cannot_change_source(self):
        _service, _policy, _lot, cycle = self._visit()
        activity = self._stage_runs(cycle, "performance").activity_id
        with self.assertRaises(ValidationError), self.cr.savepoint():
            activity.res_id = self._serials().id

    def test_unselected_revision_keeps_native_edit_semantics(self):
        _service, _policy, lot, _cycle = self._visit()
        revision = self._proof(lot)
        other = self._serials()
        revision.lot_id = other
        self.assertEqual(revision.lot_id, other)

    def test_checklist_result_change_withdraws_fen_without_header_write(self):
        service, _policy, lot, cycle = self._visit()
        rnd, _trn = self._pair(service, lot)
        rnd.chequeo_ids[:1].resultado = "no_ok"
        self.assertEqual(rnd.resultado, "rechazado")
        self.assertEqual(self._stage_runs(cycle, "fen").outcome, "cancelled")
        self.assertEqual(self._stage_runs(cycle, "rejection_performance").outcome, "pending")

    def test_blocking_finding_creation_starts_resolution_without_header_write(self):
        service, _policy, lot, cycle = self._visit()
        rnd, _trn = self._pair(service, lot)
        self._finding(rnd)
        self.assertEqual(rnd.resultado, "rechazado")
        self.assertTrue(self._stage_runs(cycle, "rejection_performance"))

    def test_finding_escalation_reconciles_without_header_write(self):
        service, _policy, lot, cycle = self._visit()
        rnd, _trn = self._pair(service, lot)
        finding = self._finding(rnd, "informativo")
        finding.severidad = "impide_operar"
        self.assertEqual(rnd.resultado, "rechazado")
        self.assertTrue(self._stage_runs(cycle, "rejection_performance"))

    def test_removing_blocking_finding_restores_fen_eligibility(self):
        service, _policy, lot, cycle = self._visit()
        rnd, trn = self._proof(lot), self._proof(lot, "terreno")
        finding = self._finding(rnd)
        service._select_evidence(lot, rnd=rnd, trn=trn)
        (rnd | trn).action_confirmar()
        resolution = self._stage_runs(cycle, "rejection_performance")
        finding.unlink()
        self.assertEqual(rnd.resultado, "aprobado")
        self.assertEqual(resolution.outcome, "business_done")
        self.assertEqual(self._stage_runs(cycle, "fen").outcome, "pending")

    def test_unrelated_detail_edit_keeps_pending_after_blocked_fen_cancel(self):
        service, _policy, lot, cycle = self._visit()
        rnd, _trn = self._pair(service, lot)
        with assert_automatic_close_rejected(self, self._stage_runs(cycle, "fen")):
            self._stage_runs(cycle, "fen").activity_id.action_cancel()
        rnd.chequeo_ids[:1].detalle = "Solo aclara la medición"
        self.assertEqual(len(self._stage_runs(cycle, "fen")), 1)
        self.assertEqual(self._stage_runs(cycle, "fen").outcome, "pending")

    def test_atomic_selection_preserves_previous_pair_on_bad_second_proof(self):
        service, _policy, lot, cycle = self._visit()
        rnd, trn = self._pair(service, lot)
        other = self._proof(self._serials(), "terreno")
        with self.assertRaises(ValidationError), self.cr.savepoint():
            service._select_evidence(lot, rnd=self._proof(lot), trn=other, reason="QA atomicidad")
        self.assertEqual(cycle.rnd_id, rnd)
        self.assertEqual(cycle.trn_id, trn)

    def test_foreign_recipient_configuration_does_not_expand_company(self):
        service, policy, lot, cycle = self._visit()
        with patch.object(
            type(self.env["res.company"]), "_create_internal_project_task", create=True
        ):
            company = self.env["res.company"].create({"name": "QA destinatario ajeno"})
        user = new_test_user(
            self.env,
            login="qa_acceptance_other_company",
            groups="stock.group_stock_user",
            company_id=company.id,
            company_ids=[Command.set(company.ids)],
        )
        policy.user_id = user
        rnd = self._proof(lot)
        rnd.chequeo_ids[:1].resultado = "no_ok"
        service._select_evidence(lot, rnd=rnd)
        rnd.action_confirmar()
        self.assertFalse(self._stage_runs(cycle, "rejection_performance"))
        self.assertEqual(user.company_ids, company)
