"""Fixtures propios de ingeniería, sin depender de tipos/etapas de demostración."""

from unittest.mock import patch

from odoo import Command
from odoo.tests.common import TransactionCase, new_test_user

from odoo.addons.mc_rov.models.stock_lot import ROV_CATEG_PARAM


class EngineeringActivityCommon(TransactionCase):
    """ECO de producto y aprobador reales, transaccionales y aislados del piloto."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context={
                **cls.env.context,
                "no_reset_password": True,
                "mail_create_nosubscribe": True,
                "tracking_disable": True,
            }
        )
        cls.rov_category = cls.env["product.category"].create({"name": "QA Ingeniería ROV"})
        cls.env["ir.config_parameter"].sudo().set_param(ROV_CATEG_PARAM, str(cls.rov_category.id))
        cls.product = cls.env["product.product"].create(
            {"name": "QA Ingeniería producto", "categ_id": cls.rov_category.id}
        )
        cls.prepare_user = new_test_user(
            cls.env, login="qa_engineering_prepare", groups="mrp_plm.group_plm_user"
        )
        cls.apply_user = new_test_user(
            cls.env, login="qa_engineering_apply", groups="mrp_plm.group_plm_user"
        )
        cls.coordinator = new_test_user(
            cls.env,
            login="qa_engineering_coordinate",
            groups="mrp_plm.group_plm_user,mc_rov.group_work_assignment_coordinate",
        )
        cls.outsider = new_test_user(
            cls.env, login="qa_engineering_internal", groups="base.group_user"
        )
        cls.eco_type = cls.env["mrp.eco.type"].create({"name": "QA Ingeniería tipo propio"})
        cls.prepare_stage = cls.env["mrp.eco.stage"].create(
            {
                "name": "QA Preparación",
                "sequence": 10,
                "type_ids": [Command.set(cls.eco_type.ids)],
                "allow_apply_change": False,
            }
        )
        cls.apply_stage = cls.env["mrp.eco.stage"].create(
            {
                "name": "QA Aplicación",
                "sequence": 20,
                "type_ids": [Command.set(cls.eco_type.ids)],
                "allow_apply_change": True,
            }
        )
        cls.approval_template = cls.env["mrp.eco.approval.template"].create(
            {
                "name": "QA Aprobación obligatoria",
                "stage_id": cls.prepare_stage.id,
                "approval_type": "mandatory",
                "user_ids": [Command.set(cls.prepare_user.ids)],
            }
        )

    def _policy_model(self):
        self.assertIn(
            "mc.rov.engineering.activity.policy",
            self.env.registry.models,
            "Missing engineering activity policy",
        )
        return self.env["mc.rov.engineering.activity.policy"]

    def _policy(self, **values):
        model = self._policy_model()
        data = {
            "enabled": True,
            "prepare_user_id": self.prepare_user.id,
            "apply_user_id": self.apply_user.id,
            "tz": "America/Santiago",
            "lead_years": 1,
            **values,
        }
        policy = model.search([("company_id", "=", self.env.company.id)], limit=1)
        if policy:
            policy.write(data)
            return policy
        return model.create({"company_id": self.env.company.id, **data})

    def _eco(self, **values):
        return self.env["mrp.eco"].create(
            {
                "name": "QA Cambio propio",
                "type": "product",
                "type_id": self.eco_type.id,
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "stage_id": self.prepare_stage.id,
                "company_id": self.env.company.id,
                **values,
            }
        )

    def _other_company(self):
        # El aprovisionamiento de proyectos internos es ajeno a estas pruebas.
        with patch.object(
            type(self.env["res.company"]), "_create_internal_project_task", create=True
        ):
            return self.env["res.company"].create({"name": "QA Ingeniería otra empresa"})
