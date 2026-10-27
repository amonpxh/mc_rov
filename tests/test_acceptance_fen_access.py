import json

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .test_mc_rov_revision import RevisionCommon


@tagged("post_install", "-at_install")
class TestAcceptanceFenAccess(RevisionCommon):
    """Abrir la ficha no requiere consultar definiciones técnicas de acciones."""

    def _user(self, coordinator=False):
        groups = "stock.group_stock_user,mrp.group_mrp_user"
        if coordinator:
            groups += ",mc_rov.group_work_assignment_team,mc_rov.group_work_assignment_coordinate"
        return new_test_user(self.env, login="qa_fen_action_access", groups=groups)

    def _open(self, coordinator=False):
        user = self._user(coordinator)
        rnd = self._revision(tipo="rendimiento")
        trn = self._revision(tipo="terreno")
        self.lot.with_user(user).check_access("read")
        with self.assertRaises(AccessError):
            self.env["ir.actions.act_window"].with_user(user).check_access("read")
        try:
            action = self.lot.with_user(user).action_preparar_ficha_equipo_nuevo()
        except AccessError as error:
            self.fail(f"Abrir la ficha exige acceso técnico a acciones: {error}")
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "mc.rov.ficha.equipo.nuevo.wizard")
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"]["default_lot_id"], self.lot.id)
        self.assertEqual(action["context"]["default_rnd_id"], rnd.id)
        self.assertEqual(action["context"]["default_trn_id"], trn.id)
        json.dumps(action)

    def test_workshop_opens_fen_without_technical_action_access(self):
        self._open()

    def test_supervisor_opens_fen_without_technical_action_access(self):
        self._open(coordinator=True)

    def test_restricted_lot_cannot_open_fen(self):
        user = self._user()
        self.env["ir.rule"].create(
            {
                "name": "QA FEN equipo restringido",
                "model_id": self.env["ir.model"]._get_id("stock.lot"),
                "domain_force": repr([("id", "!=", self.lot.id)]),
            }
        )
        self.env.invalidate_all()
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.lot.with_user(user).action_preparar_ficha_equipo_nuevo()
