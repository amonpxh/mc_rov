from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestMcRovComponente(TransactionCase):
    """Tests para mc.rov.componente, mc.rov.subtipo, mc.rov.accion y mc.rov.linea.falla."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "ROV Test",
                "tracking": "serial",
            }
        )
        cls.componente = cls.env["mc.rov.componente"].create({"name": "Motor Test"})
        cls.accion = cls.env["mc.rov.accion"].create({"name": "Reparación Test"})

    def setUp(self):
        super().setUp()
        self.order = self.env["repair.order"].create(
            {
                "product_id": self.product.id,
            }
        )

    # --- mc.rov.componente ---

    def test_componente_se_crea_con_nombre(self):
        comp = self.env["mc.rov.componente"].create({"name": "Cámara"})
        self.assertEqual(comp.name, "Cámara")

    def test_componente_active_por_defecto_es_true(self):
        comp = self.env["mc.rov.componente"].create({"name": "Sensor"})
        self.assertTrue(comp.active)

    def test_componente_se_puede_archivar(self):
        comp = self.env["mc.rov.componente"].create({"name": "Estructura"})
        comp.active = False
        self.assertFalse(comp.active)

    def test_componente_subtipo_ids_vacio_por_defecto(self):
        comp = self.env["mc.rov.componente"].create({"name": "Umbilical"})
        self.assertFalse(comp.subtipo_ids)

    def test_componente_subtipo_ids_acumula_subtipos(self):
        comp = self.env["mc.rov.componente"].create({"name": "Consola"})
        self.env["mc.rov.subtipo"].create({"name": "Monitor", "componente_id": comp.id})
        self.env["mc.rov.subtipo"].create({"name": "NUC/PC", "componente_id": comp.id})
        self.assertEqual(len(comp.subtipo_ids), 2)

    # --- mc.rov.subtipo ---

    def test_subtipo_se_crea_con_nombre_y_componente(self):
        subtipo = self.env["mc.rov.subtipo"].create(
            {
                "name": "Rotor",
                "componente_id": self.componente.id,
            }
        )
        self.assertEqual(subtipo.name, "Rotor")
        self.assertEqual(subtipo.componente_id, self.componente)

    def test_subtipo_active_por_defecto_es_true(self):
        subtipo = self.env["mc.rov.subtipo"].create(
            {
                "name": "Hélice",
                "componente_id": self.componente.id,
            }
        )
        self.assertTrue(subtipo.active)

    def test_subtipo_se_puede_archivar(self):
        subtipo = self.env["mc.rov.subtipo"].create(
            {
                "name": "ESC",
                "componente_id": self.componente.id,
            }
        )
        subtipo.active = False
        self.assertFalse(subtipo.active)

    def test_eliminar_componente_elimina_sus_subtipos(self):
        """ondelete='cascade': borrar el componente debe borrar sus subtipos."""
        comp = self.env["mc.rov.componente"].create({"name": "Temporal"})
        subtipo = self.env["mc.rov.subtipo"].create(
            {
                "name": "SubTemporal",
                "componente_id": comp.id,
            }
        )
        subtipo_id = subtipo.id
        comp.unlink()
        self.assertFalse(self.env["mc.rov.subtipo"].browse(subtipo_id).exists())

    # --- mc.rov.accion ---

    def test_accion_se_crea_con_nombre(self):
        accion = self.env["mc.rov.accion"].create({"name": "Limpieza"})
        self.assertEqual(accion.name, "Limpieza")

    def test_accion_active_por_defecto_es_true(self):
        accion = self.env["mc.rov.accion"].create({"name": "Soldadura"})
        self.assertTrue(accion.active)

    def test_accion_se_puede_archivar(self):
        accion = self.env["mc.rov.accion"].create({"name": "Calibración"})
        accion.active = False
        self.assertFalse(accion.active)

    # --- mc.rov.linea.falla ---

    def test_linea_falla_sequence_por_defecto_es_10(self):
        linea = self.env["mc.rov.linea.falla"].create(
            {
                "repair_id": self.order.id,
                "componente_id": self.componente.id,
                "accion_id": self.accion.id,
            }
        )
        self.assertEqual(linea.sequence, 10)

    def test_linea_falla_detalle_es_opcional(self):
        linea = self.env["mc.rov.linea.falla"].create(
            {
                "repair_id": self.order.id,
                "componente_id": self.componente.id,
                "accion_id": self.accion.id,
            }
        )
        self.assertFalse(linea.detalle)

    def test_linea_falla_subtipo_es_opcional(self):
        linea = self.env["mc.rov.linea.falla"].create(
            {
                "repair_id": self.order.id,
                "componente_id": self.componente.id,
                "accion_id": self.accion.id,
            }
        )
        self.assertFalse(linea.subtipo_id)

    def test_linea_falla_fecha_es_opcional(self):
        """Nada obliga a que la línea tenga fecha, aunque desde 19.0.5.2.0 traiga una.

        El nombre de este test siempre dijo "opcional" y comprobaba otra cosa: que el
        campo nacía vacío. Eso era un accidente de que no tuviera default, no la
        propiedad que vale la pena proteger. Lo que sigue siendo cierto es que se puede
        dejar en blanco.
        """
        linea = self.env["mc.rov.linea.falla"].create(
            {
                "repair_id": self.order.id,
                "componente_id": self.componente.id,
                "accion_id": self.accion.id,
            }
        )

        linea.fecha = False

        self.assertFalse(linea.fecha)

    def test_linea_falla_horas_por_defecto_es_cero(self):
        linea = self.env["mc.rov.linea.falla"].create(
            {
                "repair_id": self.order.id,
                "componente_id": self.componente.id,
                "accion_id": self.accion.id,
            }
        )
        self.assertEqual(linea.horas, 0.0)

    def test_linea_falla_acepta_distintas_acciones(self):
        """accion_id es un Many2one: distintos registros mc.rov.accion deben funcionar."""
        accion2 = self.env["mc.rov.accion"].create({"name": "Cambio completo Test"})
        linea1 = self.env["mc.rov.linea.falla"].create(
            {
                "repair_id": self.order.id,
                "componente_id": self.componente.id,
                "accion_id": self.accion.id,
            }
        )
        linea2 = self.env["mc.rov.linea.falla"].create(
            {
                "repair_id": self.order.id,
                "componente_id": self.componente.id,
                "accion_id": accion2.id,
            }
        )
        self.assertEqual(linea1.accion_id, self.accion)
        self.assertEqual(linea2.accion_id, accion2)
