from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestMcRovComponente(TransactionCase):
    """Tests para mc.rov.componente, mc.rov.subtipo y mc.rov.linea.falla."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'ROV Test',
            'tracking': 'serial',
        })
        cls.componente = cls.env['mc.rov.componente'].create({'name': 'Motor Test'})

    def setUp(self):
        super().setUp()
        self.order = self.env['repair.order'].create({
            'product_id': self.product.id,
        })

    # --- mc.rov.componente ---

    def test_componente_se_crea_con_nombre(self):
        comp = self.env['mc.rov.componente'].create({'name': 'Cámara'})
        self.assertEqual(comp.name, 'Cámara')

    def test_componente_active_por_defecto_es_true(self):
        comp = self.env['mc.rov.componente'].create({'name': 'Sensor'})
        self.assertTrue(comp.active)

    def test_componente_se_puede_archivar(self):
        comp = self.env['mc.rov.componente'].create({'name': 'Estructura'})
        comp.active = False
        self.assertFalse(comp.active)

    def test_componente_subtipo_ids_vacio_por_defecto(self):
        comp = self.env['mc.rov.componente'].create({'name': 'Umbilical'})
        self.assertFalse(comp.subtipo_ids)

    def test_componente_subtipo_ids_acumula_subtipos(self):
        comp = self.env['mc.rov.componente'].create({'name': 'Consola'})
        self.env['mc.rov.subtipo'].create({'name': 'Monitor', 'componente_id': comp.id})
        self.env['mc.rov.subtipo'].create({'name': 'NUC/PC', 'componente_id': comp.id})
        self.assertEqual(len(comp.subtipo_ids), 2)

    # --- mc.rov.subtipo ---

    def test_subtipo_se_crea_con_nombre_y_componente(self):
        subtipo = self.env['mc.rov.subtipo'].create({
            'name': 'Rotor',
            'componente_id': self.componente.id,
        })
        self.assertEqual(subtipo.name, 'Rotor')
        self.assertEqual(subtipo.componente_id, self.componente)

    def test_subtipo_active_por_defecto_es_true(self):
        subtipo = self.env['mc.rov.subtipo'].create({
            'name': 'Hélice',
            'componente_id': self.componente.id,
        })
        self.assertTrue(subtipo.active)

    def test_subtipo_se_puede_archivar(self):
        subtipo = self.env['mc.rov.subtipo'].create({
            'name': 'ESC',
            'componente_id': self.componente.id,
        })
        subtipo.active = False
        self.assertFalse(subtipo.active)

    def test_eliminar_componente_elimina_sus_subtipos(self):
        """ondelete='cascade': borrar el componente debe borrar sus subtipos."""
        comp = self.env['mc.rov.componente'].create({'name': 'Temporal'})
        subtipo = self.env['mc.rov.subtipo'].create({
            'name': 'SubTemporal',
            'componente_id': comp.id,
        })
        subtipo_id = subtipo.id
        comp.unlink()
        self.assertFalse(self.env['mc.rov.subtipo'].browse(subtipo_id).exists())

    # --- mc.rov.linea.falla ---

    def test_linea_falla_sequence_por_defecto_es_10(self):
        linea = self.env['mc.rov.linea.falla'].create({
            'repair_id': self.order.id,
            'componente_id': self.componente.id,
            'accion': 'reparacion',
        })
        self.assertEqual(linea.sequence, 10)

    def test_linea_falla_detalle_es_opcional(self):
        linea = self.env['mc.rov.linea.falla'].create({
            'repair_id': self.order.id,
            'componente_id': self.componente.id,
            'accion': 'limpieza',
        })
        self.assertFalse(linea.detalle)

    def test_linea_falla_subtipo_es_opcional(self):
        linea = self.env['mc.rov.linea.falla'].create({
            'repair_id': self.order.id,
            'componente_id': self.componente.id,
            'accion': 'calibracion',
        })
        self.assertFalse(linea.subtipo_id)

    def test_linea_falla_acepta_todas_las_acciones(self):
        acciones = [
            'cambio_completo', 'cambio_componente', 'reparacion',
            'mantencion_preventiva', 'limpieza', 'calibracion',
            'configuracion', 'soldadura', 'sin_solucion', 'derivado',
        ]
        for accion in acciones:
            linea = self.env['mc.rov.linea.falla'].create({
                'repair_id': self.order.id,
                'componente_id': self.componente.id,
                'accion': accion,
            })
            self.assertEqual(linea.accion, accion)
