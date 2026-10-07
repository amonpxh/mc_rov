from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .test_mc_rov_revision import RevisionCommon


@tagged("post_install", "-at_install")
class TestRevisionNavegacion(RevisionCommon):
    """Los accesos salen al equipo/visita exactos sin saltarse sus permisos."""

    def _accion(self, revision, nombre):
        accion = getattr(revision, nombre, None)
        self.assertTrue(callable(accion), "Falta el acceso nativo desde la revision")
        return accion()

    def test_destinos_vinculados_no_modifican_la_revision(self):
        orden = self.env["repair.order"].create(
            {"product_id": self.product.id, "lot_id": self.lot.id}
        )
        revision = self._revision(repair_id=orden.id)
        for estado in ("borrador", "confirmado"):
            revision.estado = estado
            antes = revision.read(["lot_id", "repair_id", "estado", "write_date"])
            for metodo, modelo, destino in (
                ("action_abrir_equipo", "stock.lot", self.lot.id),
                ("action_abrir_orden", "repair.order", orden.id),
            ):
                with self.subTest(estado=estado, destino=modelo):
                    accion = self._accion(revision, metodo)
                    self.assertEqual(accion["res_model"], modelo)
                    self.assertEqual(accion["res_id"], destino)
                    self.assertEqual(accion["view_mode"], "form")
                    self.assertEqual(accion["target"], "current")
                    self.assertEqual(accion["type"], "ir.actions.act_window")
            self.assertEqual(revision.read(["lot_id", "repair_id", "estado", "write_date"]), antes)

    def test_pruebas_sin_visita_no_abren_una_orden_ajena(self):
        for tipo in ("rendimiento", "terreno"):
            with self.subTest(tipo=tipo):
                revision = self._revision(tipo=tipo)
                self.assertFalse(self._accion(revision, "action_abrir_orden"))
                self.assertEqual(
                    self._accion(revision, "action_abrir_equipo")["res_id"], self.lot.id
                )

    def test_accesos_respetan_reglas_del_destino(self):
        usuario = new_test_user(
            self.env,
            login="revision_navegacion",
            groups="stock.group_stock_user",
        )
        orden = self.env["repair.order"].create(
            {"product_id": self.product.id, "lot_id": self.lot.id}
        )
        revision = self._revision(repair_id=orden.id).with_user(usuario)
        for modelo, destino, metodo in (
            ("stock.lot", self.lot.id, "action_abrir_equipo"),
            ("repair.order", orden.id, "action_abrir_orden"),
        ):
            with self.subTest(modelo=modelo):
                self.assertEqual(self._accion(revision, metodo)["res_id"], destino)
                regla = self.env["ir.rule"].create(
                    {
                        "name": "Destino no accesible",
                        "model_id": self.env["ir.model"]._get_id(modelo),
                        "domain_force": str([("id", "!=", destino)]),
                    }
                )
                with self.assertRaises(AccessError):
                    self._accion(revision, metodo)
                regla.unlink()
