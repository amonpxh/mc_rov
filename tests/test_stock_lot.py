from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

from odoo.addons.mc_rov.models.stock_lot import (
    CICLO_MANTENCION_PARAM,
    ROV_CATEG_PARAM,
)


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
class StockLotOrdenesCommon(TransactionCase):
    """Fixtures de los tests de stock.lot que dependen de órdenes de reparación.

    No declara tests: las clases concretas heredan de ella. Están separadas porque
    juntas superaban el límite de métodos públicos de pylint, que en este caso acertaba
    — eran tres asuntos distintos en una sola clase.

    No necesita el árbol de categorías de TestStockLotRov: lo que miran estos tests es
    la relación con repair.order, no con el producto.
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
        cls.tipo_mantencion = cls.env.ref("mc_rov.tipo_mantencion_preventiva")
        cls.tipo_correctiva = cls.env.ref("mc_rov.tipo_reparacion_correctiva")

    def setUp(self):
        super().setUp()
        # Lote nuevo por cada test para garantizar aislamiento
        self.lot = self.env["stock.lot"].create(
            {
                "name": "ROV-001",
                "product_id": self.product.id,
            }
        )

    def _orden(self, tipos=None, **vals):
        """Crea una orden de reparación para self.lot con los tipos y valores dados."""
        if tipos is not None:
            vals["tipo_intervencion_ids"] = [(6, 0, tipos.ids)]
        return self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "lot_id": self.lot.id,
                **vals,
            }
        )


@tagged("post_install", "-at_install")
class TestStockLotContadores(StockLotOrdenesCommon):
    """Tests de mc_repair_count y mc_mantencion_count."""

    def test_repair_count_sin_reparaciones_es_cero(self):
        self.assertEqual(self.lot.mc_repair_count, 0)

    def test_repair_count_no_cuenta_ordenes_en_borrador(self):
        """Solo las órdenes 'done' cuentan — una en draft no debe sumar."""
        self._orden(tipos=self.tipo_correctiva)
        self.assertEqual(self.lot.mc_repair_count, 0)

    def test_repair_count_cuenta_ordenes_done(self):
        self._orden(tipos=self.tipo_correctiva, state="done")
        self.assertEqual(self.lot.mc_repair_count, 1)

    def test_repair_count_acumula_multiples_done(self):
        for _ in range(3):
            self._orden(tipos=self.tipo_correctiva, state="done")
        self.assertEqual(self.lot.mc_repair_count, 3)

    def test_repair_count_no_cuenta_mantenciones(self):
        """El botón decía 5 cuando eran 3 reparaciones y 2 mantenciones."""
        self._orden(tipos=self.tipo_mantencion, state="done")
        self.assertEqual(self.lot.mc_repair_count, 0)
        self.assertEqual(self.lot.mc_mantencion_count, 1)

    def test_contadores_cuentan_la_visita_mixta_en_ambos(self):
        """Una visita que fue las dos cosas suma en los dos contadores."""
        self._orden(tipos=self.tipo_mantencion | self.tipo_correctiva, state="done")
        self.assertEqual(self.lot.mc_repair_count, 1)
        self.assertEqual(self.lot.mc_mantencion_count, 1)

    def test_contadores_ignoran_tipos_que_no_son_ninguna_de_las_dos(self):
        """Un diagnóstico no es reparación ni mantención."""
        self._orden(tipos=self.env.ref("mc_rov.tipo_diagnostico"), state="done")
        self.assertEqual(self.lot.mc_repair_count, 0)
        self.assertEqual(self.lot.mc_mantencion_count, 0)


@tagged("post_install", "-at_install")
class TestStockLotFechas(StockLotOrdenesCommon):
    """Tests de ultima_mantencion, ultima_reparacion y el sellado de fecha_entrega_real."""

    def test_ultima_mantencion_sin_reparaciones_es_false(self):
        self.assertFalse(self.lot.ultima_mantencion)

    def test_ultima_mantencion_retorna_fecha_entrega_real(self):
        hoy = fields.Date.today()
        self._orden(
            tipos=self.tipo_mantencion,
            state="done",
            fecha_entrega_real=hoy,
        )
        self.assertEqual(self.lot.ultima_mantencion, hoy)

    def test_ultima_mantencion_ignora_reparaciones_correctivas(self):
        """Una reparación no es una mantención.

        Un equipo reparado en marzo sigue debiendo su mantención anual: si la correctiva
        actualizara este campo, el vencimiento quedaría oculto.
        """
        self._orden(
            tipos=self.tipo_correctiva,
            state="done",
            fecha_entrega_real=fields.Date.today(),
        )
        self.assertFalse(self.lot.ultima_mantencion)

    def test_ultima_mantencion_cuenta_la_visita_mixta(self):
        """Si el equipo entró a mantención y de paso se reparó, la mantención cuenta.

        Es el caso que motivó pasar tipo_intervencion a múltiple: antes había que elegir
        uno de los dos y, si se elegía la reparación, el ciclo no se reiniciaba.
        """
        hoy = fields.Date.today()
        self._orden(
            tipos=self.tipo_mantencion | self.tipo_correctiva,
            state="done",
            fecha_entrega_real=hoy,
        )
        self.assertEqual(self.lot.ultima_mantencion, hoy)

    def test_ultima_mantencion_toma_la_fecha_mas_reciente_no_el_ultimo_id(self):
        """Las órdenes no se cierran en el orden en que se crean."""
        reciente = fields.Date.to_date("2026-06-01")
        antigua = fields.Date.to_date("2025-06-01")

        self._orden(
            tipos=self.tipo_mantencion,
            state="done",
            fecha_entrega_real=reciente,
        )
        # Se crea después, así que tiene id mayor pese a ser la más antigua
        self._orden(
            tipos=self.tipo_mantencion,
            state="done",
            fecha_entrega_real=antigua,
        )

        self.assertEqual(self.lot.ultima_mantencion, reciente)

    def test_ultima_mantencion_es_false_si_orden_done_sin_fecha_entrega(self):
        """Una orden done sin fecha no debe mostrar fecha ni colarse por el orden DESC.

        Desde 19.0.4.1.0 el cierre sella la fecha, así que este caso solo llega desde
        datos anteriores a esa versión. La fecha se borra explícitamente para
        reproducirlos.
        """
        orden = self._orden(tipos=self.tipo_mantencion, state="done")
        orden.fecha_entrega_real = False

        self.assertFalse(self.lot.ultima_mantencion)

    def test_ultima_mantencion_ignora_ordenes_en_borrador(self):
        """Si solo hay órdenes en draft, ultima_mantencion debe quedar vacía."""
        self._orden(
            tipos=self.tipo_mantencion,
            fecha_entrega_real=fields.Date.today(),
        )
        self.assertFalse(self.lot.ultima_mantencion)

    # --- ultima_reparacion ---

    def test_ultima_reparacion_sin_ordenes_es_false(self):
        self.assertFalse(self.lot.ultima_reparacion)

    def test_ultima_reparacion_ignora_mantenciones(self):
        """Simétrico al caso inverso: una mantención no es una reparación."""
        self._orden(
            tipos=self.tipo_mantencion,
            state="done",
            fecha_entrega_real=fields.Date.today(),
        )
        self.assertFalse(self.lot.ultima_reparacion)

    def test_ultima_reparacion_ignora_diagnosticos(self):
        """Un diagnóstico no repara nada: no lleva ninguna de las dos casillas."""
        self._orden(
            tipos=self.env.ref("mc_rov.tipo_diagnostico"),
            state="done",
            fecha_entrega_real=fields.Date.today(),
        )
        self.assertFalse(self.lot.ultima_reparacion)

    def test_visita_mixta_actualiza_las_dos_fechas(self):
        hoy = fields.Date.today()
        self._orden(
            tipos=self.tipo_mantencion | self.tipo_correctiva,
            state="done",
            fecha_entrega_real=hoy,
        )
        self.assertEqual(self.lot.ultima_mantencion, hoy)
        self.assertEqual(self.lot.ultima_reparacion, hoy)

    # --- Sellado automático de fecha_entrega_real ---

    def test_cerrar_orden_sin_fecha_la_completa_sola(self):
        """El técnico cerraba la orden sin fecha y la mantención no contaba.

        Ese era el modo de falla: sin advertencia alguna, el equipo quedaba vencido
        para siempre pese a habérsele hecho la mantención.
        """
        orden = self._orden(tipos=self.tipo_mantencion, state="confirmed")
        self.assertFalse(orden.fecha_entrega_real)

        orden.state = "done"

        self.assertEqual(orden.fecha_entrega_real, fields.Date.context_today(orden))
        self.assertEqual(self.lot.ultima_mantencion, orden.fecha_entrega_real)

    def test_cerrar_orden_no_pisa_una_fecha_ya_puesta(self):
        """Si la entrega al cliente fue otro día, manda lo que escribió el técnico."""
        ayer = fields.Date.subtract(fields.Date.today(), days=1)
        orden = self._orden(
            tipos=self.tipo_mantencion,
            state="confirmed",
            fecha_entrega_real=ayer,
        )

        orden.state = "done"

        self.assertEqual(orden.fecha_entrega_real, ayer)


@tagged("post_install", "-at_install")
class TestStockLotEstadoOperativo(StockLotOrdenesCommon):
    """Tests de mc_estado_operativo, derivado de las órdenes abiertas."""

    def test_estado_operativo_sin_ordenes_es_operativo(self):
        self.assertEqual(self.lot.mc_estado_operativo, "Operativo")

    def test_estado_operativo_con_orden_abierta_es_en_reparacion(self):
        self._orden(tipos=self.tipo_correctiva, state="confirmed")
        self.assertEqual(self.lot.mc_estado_operativo, "En reparación")

    def test_estado_operativo_con_mantencion_abierta_es_en_mantencion(self):
        self._orden(tipos=self.tipo_mantencion, state="confirmed")
        self.assertEqual(self.lot.mc_estado_operativo, "En mantención")

    def test_estado_operativo_en_visita_mixta_es_en_mantencion(self):
        """Si la visita incluye mantención, esa manda sobre la reparación."""
        self._orden(tipos=self.tipo_mantencion | self.tipo_correctiva, state="confirmed")
        self.assertEqual(self.lot.mc_estado_operativo, "En mantención")

    def test_estado_operativo_ignora_ordenes_en_borrador(self):
        """Un borrador es una cotización: el equipo todavía no entró al taller."""
        self._orden(tipos=self.tipo_correctiva)
        self.assertEqual(self.lot.mc_estado_operativo, "Operativo")

    def test_estado_operativo_vuelve_a_operativo_al_cerrar_la_orden(self):
        """Cerrar la orden devuelve el equipo a operativo sin intervención manual."""
        orden = self._orden(tipos=self.tipo_correctiva, state="confirmed")
        self.assertEqual(self.lot.mc_estado_operativo, "En reparación")

        orden.state = "done"

        self.assertEqual(self.lot.mc_estado_operativo, "Operativo")


@tagged("post_install", "-at_install")
class TestStockLotCicloMantencion(StockLotOrdenesCommon):
    """Tests de proxima_mantencion y del ciclo configurable."""

    def test_sin_puesta_en_servicio_no_hay_reloj(self):
        """Un equipo en bodega no debe ensuciar la lista de vencidos."""
        self.assertFalse(self.lot.proxima_mantencion)

    def test_cuenta_doce_meses_desde_la_puesta_en_servicio(self):
        entrega = fields.Date.to_date("2026-03-15")
        self.lot.mc_fecha_puesta_servicio = entrega

        self.assertEqual(self.lot.proxima_mantencion, entrega + relativedelta(months=12))

    def test_la_mantencion_hecha_manda_sobre_la_puesta_en_servicio(self):
        self.lot.mc_fecha_puesta_servicio = fields.Date.to_date("2026-01-01")
        mantencion = fields.Date.to_date("2026-04-01")

        self._orden(
            tipos=self.tipo_mantencion,
            state="done",
            fecha_entrega_real=mantencion,
        )

        self.assertEqual(self.lot.proxima_mantencion, mantencion + relativedelta(months=12))

    def test_el_contador_parte_cuando_se_hizo_la_mantencion_no_en_el_aniversario(self):
        """Si la mantención se hizo a los 18 meses, el ciclo parte ahí.

        Lo que importa es cuándo se intervino de verdad, no el aniversario teórico de
        la entrega.
        """
        entrega = fields.Date.to_date("2025-01-01")
        self.lot.mc_fecha_puesta_servicio = entrega
        tardia = entrega + relativedelta(months=18)

        self._orden(
            tipos=self.tipo_mantencion,
            state="done",
            fecha_entrega_real=tardia,
        )

        self.assertEqual(self.lot.proxima_mantencion, tardia + relativedelta(months=12))

    def test_una_reparacion_no_reinicia_el_ciclo(self):
        entrega = fields.Date.to_date("2026-01-01")
        self.lot.mc_fecha_puesta_servicio = entrega

        self._orden(
            tipos=self.tipo_correctiva,
            state="done",
            fecha_entrega_real=fields.Date.to_date("2026-06-01"),
        )

        self.assertEqual(self.lot.proxima_mantencion, entrega + relativedelta(months=12))

    def test_el_ciclo_se_puede_cambiar_sin_tocar_codigo(self):
        """El largo del ciclo vive en un parámetro de sistema, no en el módulo."""
        self.env["ir.config_parameter"].sudo().set_param(CICLO_MANTENCION_PARAM, "6")
        entrega = fields.Date.to_date("2026-03-15")

        self.lot.mc_fecha_puesta_servicio = entrega

        self.assertEqual(self.lot.proxima_mantencion, entrega + relativedelta(months=6))

    def test_un_ciclo_corrupto_cae_al_valor_por_defecto(self):
        """Un parámetro mal escrito no debe romper la ficha de todos los equipos."""
        self.env["ir.config_parameter"].sudo().set_param(CICLO_MANTENCION_PARAM, "doce")
        entrega = fields.Date.to_date("2026-03-15")

        self.lot.mc_fecha_puesta_servicio = entrega

        self.assertEqual(self.lot.proxima_mantencion, entrega + relativedelta(months=12))
