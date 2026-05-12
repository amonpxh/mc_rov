from datetime import date

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestRepairOrder(TransactionCase):
    """Tests para los campos propios de repair.order definidos en mc_rov."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'ROV Test',
            'tracking': 'serial',
        })
        cls.componente = cls.env['mc.rov.componente'].create({'name': 'Motor Test'})
        cls.accion = cls.env['mc.rov.accion'].create({'name': 'Reparación Test'})

    def setUp(self):
        super().setUp()
        self.order = self.env['repair.order'].create({
            'product_id': self.product.id,
        })

    # --- Valores por defecto ---

    def test_tipo_intervencion_por_defecto_es_false(self):
        self.assertFalse(self.order.tipo_intervencion)

    def test_estado_final_por_defecto_es_false(self):
        self.assertFalse(self.order.estado_final)

    def test_garantia_reparacion_por_defecto_es_false(self):
        self.assertFalse(self.order.garantia_reparacion)

    def test_fecha_entrega_real_por_defecto_es_false(self):
        self.assertFalse(self.order.fecha_entrega_real)

    # --- Asignación de campos ---

    def test_tipo_intervencion_acepta_valores_validos(self):
        for valor in ('diagnostico', 'reparacion_correctiva', 'mantencion_preventiva', 'conversion'):
            self.order.tipo_intervencion = valor
            self.assertEqual(self.order.tipo_intervencion, valor)

    def test_estado_final_acepta_valores_validos(self):
        for valor in ('reparado', 'no_reparado', 'derivado', 'pendiente_repuesto'):
            self.order.estado_final = valor
            self.assertEqual(self.order.estado_final, valor)

    def test_fecha_entrega_real_se_guarda(self):
        hoy = date.today()
        self.order.fecha_entrega_real = hoy
        self.assertEqual(self.order.fecha_entrega_real, hoy)

    # --- linea_falla_ids ---

    def test_linea_falla_ids_vacia_por_defecto(self):
        self.assertFalse(self.order.linea_falla_ids)

    def test_linea_falla_ids_acepta_una_linea(self):
        self.env['mc.rov.linea.falla'].create({
            'repair_id': self.order.id,
            'componente_id': self.componente.id,
            'accion_id': self.accion.id,
        })
        self.assertEqual(len(self.order.linea_falla_ids), 1)

    def test_linea_falla_ids_acumula_multiples_lineas(self):
        for _ in range(3):
            self.env['mc.rov.linea.falla'].create({
                'repair_id': self.order.id,
                'componente_id': self.componente.id,
                'accion_id': self.accion.id,
            })
        self.assertEqual(len(self.order.linea_falla_ids), 3)
