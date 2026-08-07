from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

from odoo.addons.mc_rov.models.stock_lot import ROV_CATEG_PARAM


@tagged("post_install", "-at_install")
class TestStockLotRov(TransactionCase):
    """Tests de es_un_rov, que se deriva de la categoría del producto."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Árbol propio en vez del de producción: en una BD de test el XML ID
        # __import__.cat_ROV no existe. El parámetro de sistema tiene precedencia sobre
        # ese respaldo, así que el resultado es el mismo corra donde corra.
        Category = cls.env["product.category"]
        cls.categ_rov_root = Category.create({"name": "ROV Test - Vehiculos"})
        cls.categ_rov_mc = Category.create(
            {"name": "ROV-MC Test", "parent_id": cls.categ_rov_root.id}
        )
        cls.categ_rov_xx = Category.create(
            {"name": "ROV-XX Test", "parent_id": cls.categ_rov_root.id}
        )
        cls.categ_ajena = Category.create({"name": "CNSL-PSU Test"})

        cls.env["ir.config_parameter"].sudo().set_param(
            ROV_CATEG_PARAM, str(cls.categ_rov_root.id)
        )

        # El producto se crea una vez para toda la clase (operación costosa).
        # Sin categ_id explícito hereda la genérica, que queda fuera de la rama ROV.
        cls.product = cls.env["product.product"].create(
            {
                "name": "ROV Test",
                "tracking": "serial",
            }
        )

    def _serie_en_categoria(self, categ):
        """Crea un producto en la categoría dada y le asigna un número de serie."""
        product = self.env["product.product"].create(
            {
                "name": f"Producto {categ.name}",
                "tracking": "serial",
                "categ_id": categ.id,
            }
        )
        return self.env["stock.lot"].create(
            {
                "name": f"SN-{categ.id}",
                "product_id": product.id,
            }
        )

    def setUp(self):
        super().setUp()
        # Lote nuevo por cada test para garantizar aislamiento
        self.lot = self.env["stock.lot"].create(
            {
                "name": "ROV-001",
                "product_id": self.product.id,
            }
        )

    # --- es_un_rov ---

    def test_es_un_rov_por_defecto_es_false(self):
        """Un producto sin categoría ROV no genera series marcadas como ROV."""
        self.assertFalse(self.lot.es_un_rov)

    def test_es_un_rov_true_para_vehiculo_marca_propia(self):
        self.assertTrue(self._serie_en_categoria(self.categ_rov_mc).es_un_rov)

    def test_es_un_rov_true_para_vehiculo_de_otra_marca(self):
        """Los ROV-XX entran en consignación pero igual llevan ficha técnica."""
        self.assertTrue(self._serie_en_categoria(self.categ_rov_xx).es_un_rov)

    def test_es_un_rov_true_para_subcategoria_nueva(self):
        """Una categoría agregada bajo la raíz hereda la marca sin tocar código."""
        subcateg = self.env["product.category"].create(
            {
                "name": "ROV-RENT Test",
                "parent_id": self.categ_rov_mc.id,
            }
        )
        self.assertTrue(self._serie_en_categoria(subcateg).es_un_rov)

    def test_es_un_rov_false_para_categoria_fuera_de_la_rama(self):
        self.assertFalse(self._serie_en_categoria(self.categ_ajena).es_un_rov)

    def test_es_un_rov_se_recalcula_al_mover_una_categoria(self):
        """Mover una categoría dentro de la rama ROV enciende las series que cuelgan de ella.

        Cubre el hueco que deja @api.depends("product_id.categ_id"): aquí el producto no
        cambia de categoría — es la categoría la que cambia de padre.
        """
        serie = self._serie_en_categoria(self.categ_ajena)
        self.assertFalse(serie.es_un_rov)

        self.categ_ajena.write({"parent_id": self.categ_rov_root.id})

        self.assertTrue(serie.es_un_rov)


@tagged("post_install", "-at_install")
class TestStockLotEstado(TransactionCase):
    """Tests de los campos de stock.lot que se derivan de las órdenes de reparación.

    Van en una clase aparte de TestStockLotRov porque no necesitan el árbol de
    categorías: lo que miran es la relación con repair.order, no con el producto.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # El producto se crea una vez para toda la clase (operación costosa)
        cls.product = cls.env["product.product"].create(
            {
                "name": "ROV Test",
                "tracking": "serial",
            }
        )

    def setUp(self):
        super().setUp()
        # Lote nuevo por cada test para garantizar aislamiento
        self.lot = self.env["stock.lot"].create(
            {
                "name": "ROV-001",
                "product_id": self.product.id,
            }
        )

    def _orden(self, **vals):
        """Crea una orden de reparación para self.lot con los valores dados."""
        return self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "lot_id": self.lot.id,
                **vals,
            }
        )

    # --- mc_repair_count ---

    def test_repair_count_sin_reparaciones_es_cero(self):
        self.assertEqual(self.lot.mc_repair_count, 0)

    def test_repair_count_no_cuenta_ordenes_en_borrador(self):
        """Solo las órdenes 'done' cuentan — una en draft no debe sumar."""
        self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "lot_id": self.lot.id,
            }
        )
        self.assertEqual(self.lot.mc_repair_count, 0)

    def test_repair_count_cuenta_ordenes_done(self):
        self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "lot_id": self.lot.id,
                "state": "done",
            }
        )
        self.assertEqual(self.lot.mc_repair_count, 1)

    def test_repair_count_acumula_multiples_done(self):
        for _ in range(3):
            self.env["repair.order"].create(
                {
                    "product_id": self.product.id,
                    "lot_id": self.lot.id,
                    "state": "done",
                }
            )
        self.assertEqual(self.lot.mc_repair_count, 3)

    # --- ultima_mantencion ---

    def test_ultima_mantencion_sin_reparaciones_es_false(self):
        self.assertFalse(self.lot.ultima_mantencion)

    def test_ultima_mantencion_retorna_fecha_entrega_real(self):
        hoy = fields.Date.today()
        self._orden(
            state="done",
            tipo_intervencion="mantencion_preventiva",
            fecha_entrega_real=hoy,
        )
        self.assertEqual(self.lot.ultima_mantencion, hoy)

    def test_ultima_mantencion_ignora_reparaciones_correctivas(self):
        """Una reparación no es una mantención.

        Un equipo reparado en marzo sigue debiendo su mantención anual: si la correctiva
        actualizara este campo, el vencimiento quedaría oculto.
        """
        self._orden(
            state="done",
            tipo_intervencion="reparacion_correctiva",
            fecha_entrega_real=fields.Date.today(),
        )
        self.assertFalse(self.lot.ultima_mantencion)

    def test_ultima_mantencion_toma_la_fecha_mas_reciente_no_el_ultimo_id(self):
        """Las órdenes no se cierran en el orden en que se crean."""
        reciente = fields.Date.to_date("2026-06-01")
        antigua = fields.Date.to_date("2025-06-01")

        self._orden(
            state="done",
            tipo_intervencion="mantencion_preventiva",
            fecha_entrega_real=reciente,
        )
        # Se crea después, así que tiene id mayor pese a ser la más antigua
        self._orden(
            state="done",
            tipo_intervencion="mantencion_preventiva",
            fecha_entrega_real=antigua,
        )

        self.assertEqual(self.lot.ultima_mantencion, reciente)

    def test_ultima_mantencion_es_false_si_orden_done_sin_fecha_entrega(self):
        """Una orden done sin fecha_entrega_real no debe mostrar fecha."""
        self._orden(state="done", tipo_intervencion="mantencion_preventiva")
        self.assertFalse(self.lot.ultima_mantencion)

    def test_ultima_mantencion_ignora_ordenes_en_borrador(self):
        """Si solo hay órdenes en draft, ultima_mantencion debe quedar vacía."""
        self._orden(
            tipo_intervencion="mantencion_preventiva",
            fecha_entrega_real=fields.Date.today(),
        )
        self.assertFalse(self.lot.ultima_mantencion)

    # --- mc_estado_operativo ---

    def test_estado_operativo_sin_ordenes_es_operativo(self):
        self.assertEqual(self.lot.mc_estado_operativo, "Operativo")

    def test_estado_operativo_con_orden_abierta_es_en_reparacion(self):
        self._orden(state="confirmed", tipo_intervencion="reparacion_correctiva")
        self.assertEqual(self.lot.mc_estado_operativo, "En reparación")

    def test_estado_operativo_con_mantencion_abierta_es_en_mantencion(self):
        self._orden(state="confirmed", tipo_intervencion="mantencion_preventiva")
        self.assertEqual(self.lot.mc_estado_operativo, "En mantención")

    def test_estado_operativo_ignora_ordenes_en_borrador(self):
        """Un borrador es una cotización: el equipo todavía no entró al taller."""
        self._orden(tipo_intervencion="reparacion_correctiva")
        self.assertEqual(self.lot.mc_estado_operativo, "Operativo")

    def test_estado_operativo_vuelve_a_operativo_al_cerrar_la_orden(self):
        """Cerrar la orden devuelve el equipo a operativo sin intervención manual."""
        orden = self._orden(state="confirmed", tipo_intervencion="reparacion_correctiva")
        self.assertEqual(self.lot.mc_estado_operativo, "En reparación")

        orden.state = "done"

        self.assertEqual(self.lot.mc_estado_operativo, "Operativo")
