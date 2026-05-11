from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestStockLotRov(TransactionCase):
    """Tests para los campos es_un_rov, mc_repair_count y ultima_mantencion en stock.lot."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # El producto se crea una vez para toda la clase (operación costosa)
        cls.product = cls.env['product.product'].create({
            'name': 'ROV Test',
            'tracking': 'serial',
        })

    def setUp(self):
        super().setUp()
        # Lote nuevo por cada test para garantizar aislamiento
        self.lot = self.env['stock.lot'].create({
            'name': 'ROV-001',
            'product_id': self.product.id,
        })

    # --- es_un_rov ---

    def test_es_un_rov_por_defecto_es_false(self):
        """Un lote recién creado no es ROV hasta que se marque explícitamente."""
        self.assertFalse(self.lot.es_un_rov)

    # --- mc_repair_count ---

    def test_repair_count_sin_reparaciones_es_cero(self):
        self.assertEqual(self.lot.mc_repair_count, 0)

    def test_repair_count_no_cuenta_ordenes_en_borrador(self):
        """Solo las órdenes 'done' cuentan — una en draft no debe sumar."""
        self.env['repair.order'].create({
            'product_id': self.product.id,
            'lot_id': self.lot.id,
        })
        self.assertEqual(self.lot.mc_repair_count, 0)

    def test_repair_count_cuenta_ordenes_done(self):
        self.env['repair.order'].create({
            'product_id': self.product.id,
            'lot_id': self.lot.id,
            'state': 'done',
        })
        self.assertEqual(self.lot.mc_repair_count, 1)

    def test_repair_count_acumula_multiples_done(self):
        for i in range(3):
            self.env['repair.order'].create({
                'product_id': self.product.id,
                'lot_id': self.lot.id,
                'state': 'done',
            })
        self.assertEqual(self.lot.mc_repair_count, 3)

    # --- ultima_mantencion ---

    def test_ultima_mantencion_sin_reparaciones_es_false(self):
        self.assertFalse(self.lot.ultima_mantencion)

    def test_ultima_mantencion_retorna_fecha_de_ultima_orden_done(self):
        repair = self.env['repair.order'].create({
            'product_id': self.product.id,
            'lot_id': self.lot.id,
            'state': 'done',
        })
        self.assertEqual(self.lot.ultima_mantencion, repair.create_date.date())

    def test_ultima_mantencion_ignora_ordenes_en_borrador(self):
        """Si solo hay órdenes en draft, ultima_mantencion debe quedar vacía."""
        self.env['repair.order'].create({
            'product_id': self.product.id,
            'lot_id': self.lot.id,
        })
        self.assertFalse(self.lot.ultima_mantencion)
