from datetime import date

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestRepairOrder(TransactionCase):
    """Tests para los campos propios de repair.order definidos en mc_rov."""

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

    # --- Valores por defecto ---

    def test_tipo_intervencion_por_defecto_esta_vacio(self):
        self.assertFalse(self.order.tipo_intervencion_ids)

    def test_fecha_entrega_real_por_defecto_es_false(self):
        self.assertFalse(self.order.fecha_entrega_real)

    # --- Asignación de campos ---

    def test_tipo_intervencion_acepta_los_tipos_del_catalogo(self):
        for xml_id in (
            "mc_rov.tipo_diagnostico",
            "mc_rov.tipo_reparacion_correctiva",
            "mc_rov.tipo_mantencion_preventiva",
            "mc_rov.tipo_conversion",
        ):
            tipo = self.env.ref(xml_id)
            self.order.tipo_intervencion_ids = [(6, 0, tipo.ids)]
            self.assertEqual(self.order.tipo_intervencion_ids, tipo)

    def test_tipo_intervencion_admite_varios_a_la_vez(self):
        """Una visita puede ser mantención y reparación: ese es el punto del cambio."""
        mantencion = self.env.ref("mc_rov.tipo_mantencion_preventiva")
        correctiva = self.env.ref("mc_rov.tipo_reparacion_correctiva")

        self.order.tipo_intervencion_ids = [(6, 0, (mantencion | correctiva).ids)]

        self.assertEqual(len(self.order.tipo_intervencion_ids), 2)

    def test_solo_mantencion_preventiva_cuenta_como_mantencion(self):
        """El ciclo se calcula leyendo es_mantencion, no comparando nombres."""
        self.assertTrue(self.env.ref("mc_rov.tipo_mantencion_preventiva").es_mantencion)
        for xml_id in (
            "mc_rov.tipo_diagnostico",
            "mc_rov.tipo_reparacion_correctiva",
            "mc_rov.tipo_conversion",
        ):
            self.assertFalse(self.env.ref(xml_id).es_mantencion)

    def test_fecha_entrega_real_se_guarda(self):
        hoy = date.today()
        self.order.fecha_entrega_real = hoy
        self.assertEqual(self.order.fecha_entrega_real, hoy)

    # --- linea_falla_ids ---

    def test_linea_falla_ids_vacia_por_defecto(self):
        self.assertFalse(self.order.linea_falla_ids)

    def test_linea_falla_ids_acepta_una_linea(self):
        self.env["mc.rov.linea.falla"].create(
            {
                "repair_id": self.order.id,
                "componente_id": self.componente.id,
                "accion_id": self.accion.id,
            }
        )
        self.assertEqual(len(self.order.linea_falla_ids), 1)

    def test_linea_falla_ids_acumula_multiples_lineas(self):
        for _ in range(3):
            self.env["mc.rov.linea.falla"].create(
                {
                    "repair_id": self.order.id,
                    "componente_id": self.componente.id,
                    "accion_id": self.accion.id,
                }
            )
        self.assertEqual(len(self.order.linea_falla_ids), 3)
