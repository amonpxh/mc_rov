from datetime import date

from lxml import etree

from odoo import fields
from odoo.exceptions import UserError
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
            self._linea()
        self.assertEqual(len(self.order.linea_falla_ids), 3)

    def _linea(self, **vals):
        """Crea una línea de trabajo para self.order."""
        return self.env["mc.rov.linea.falla"].create(
            {
                "repair_id": self.order.id,
                "componente_id": self.componente.id,
                "accion_id": self.accion.id,
                **vals,
            }
        )

    def test_fecha_de_la_linea_por_defecto_es_hoy(self):
        """Sin default quedaba en blanco casi siempre y no se podía situar el trabajo."""
        self.assertEqual(self._linea().fecha, fields.Date.context_today(self.order))

    def test_lineas_empatadas_en_secuencia_salen_en_orden_de_creacion(self):
        """Todas nacen en sequence = 10; el id es lo que evita que se rebarajen.

        Se consulta con search y no por el one2many: dentro de una misma transacción el
        one2many puede venir del caché en orden de inserción y el test pasaría igual
        aunque el _order estuviera mal.
        """
        for _ in range(3):
            self._linea()

        lineas = self.env["mc.rov.linea.falla"].search([("repair_id", "=", self.order.id)])

        self.assertEqual(lineas.ids, sorted(lineas.ids))

    # --- mc_total_horas ---

    def test_mc_total_horas_suma_las_lineas(self):
        self._linea(horas=1.5)
        self._linea(horas=2.0)
        self.assertEqual(self.order.mc_total_horas, 3.5)

    def test_mc_total_horas_se_puede_buscar(self):
        """Es columna de la lista: sin store no se podría ordenar, filtrar ni agrupar.

        La búsqueda es la prueba real de que está almacenado — sobre un campo no
        almacenado, este search levanta excepción.
        """
        self._linea(horas=4.0)

        encontradas = self.env["repair.order"].search([("mc_total_horas", ">", 3.0)])

        self.assertIn(self.order, encontradas)

    # --- Cierre de la orden ---

    def test_no_se_puede_cerrar_una_orden_sin_tipo_de_intervencion(self):
        """Sin tipo la orden es invisible para todo lo que se calcula a partir de ella.

        No cuenta como mantención ni reparación, no reinicia el ciclo del equipo y no
        suma a los contadores — y nada avisa. El síntoma aparece meses después.
        """
        with self.assertRaises(UserError):
            self.order.state = "done"

    def test_cerrar_con_tipo_de_intervencion_funciona(self):
        self.order.tipo_intervencion_ids = [
            (6, 0, self.env.ref("mc_rov.tipo_reparacion_correctiva").ids)
        ]

        self.order.state = "done"

        self.assertEqual(self.order.state, "done")

    def test_el_bloqueo_no_estorba_otras_escrituras(self):
        """Solo la transición a done exige el tipo; editar la orden no."""
        self.order.falla_reportada = "No enciende"
        self.assertEqual(self.order.falla_reportada, "No enciende")


@tagged("post_install", "-at_install")
class TestRepairClosingNotice(TransactionCase):
    """El aviso anticipa carencias reales de cierre; no certifica revisión ni entrega."""

    def setUp(self):
        super().setUp()
        self.product = self.env["product.product"].create({"name": "Equipo aviso QA"})
        self.order = self.env["repair.order"].create({"product_id": self.product.id})
        self.component = self.env["mc.rov.componente"].create({"name": "Componente aviso QA"})
        self.action = self.env["mc.rov.accion"].create({"name": "Acción aviso QA"})

    def _notice(self):
        self.assertIn("mc_aviso_cierre", self.order._fields, "Falta el aviso contextual de cierre")
        return self.order.mc_aviso_cierre or ""

    def _type(self):
        self.order.tipo_intervencion_ids = [(6, 0, self.env.ref("mc_rov.tipo_diagnostico").ids)]

    def _line(self, **values):
        return self.env["mc.rov.linea.falla"].create(
            {
                "repair_id": self.order.id,
                "componente_id": self.component.id,
                "accion_id": self.action.id,
                **values,
            }
        )

    def test_tipo_faltante_y_diagnostico_sin_trabajos(self):
        self.assertEqual(self._notice(), "selecciona el Tipo de intervención.")
        self._type()
        self.assertFalse(self._notice())
        self.order._validar_tipo_intervencion()
        self.order._validar_origen()
        self.order._validar_repuestos()

    def test_origen_se_actualiza_al_completar_las_lineas(self):
        self._type()
        first = self._line()
        second = self._line()
        self.assertEqual(self._notice(), "completa el Origen de 2 trabajos en Cierre.")
        first.origen = "desconocida"
        self.assertEqual(self._notice(), "completa el Origen de 1 trabajo en Cierre.")
        second.origen = "desconocida"
        self.assertFalse(self._notice())
        self.order._validar_origen()

    def test_repuesto_de_otra_orden_no_resuelve_el_aviso(self):
        self._type()
        self.action.consume_repuesto = True
        self._line(origen="desconocida")
        self.assertEqual(self._notice(), "registra los repuestos en Repuestos.")
        part = self.env["product.product"].create({"name": "Repuesto aviso QA", "type": "consu"})
        other = self.env["repair.order"].create({"product_id": self.product.id})

        def add_part(order):
            return self.env["stock.move"].create(
                {
                    "repair_id": order.id,
                    "repair_line_type": "add",
                    "product_id": part.id,
                    "product_uom_qty": 1,
                    "location_id": order.location_id.id,
                    "location_dest_id": order.location_dest_id.id,
                }
            )

        add_part(other)
        self.assertTrue(self._notice())
        with self.assertRaises(UserError):
            self.order._validar_repuestos()
        add_part(self.order)
        self.assertFalse(self._notice())
        self.order._validar_repuestos()

    def test_combina_solo_carencias_aplicables(self):
        line = self._line()
        self.action.consume_repuesto = True
        self.assertEqual(
            self._notice(),
            "selecciona el Tipo de intervención, completa el Origen de 1 trabajo en Cierre "
            "y registra los repuestos en Repuestos.",
        )
        self.action.consume_repuesto = False
        line.origen = "desconocida"
        self.assertEqual(self._notice(), "selecciona el Tipo de intervención.")

    def test_cerrada_o_cancelada_no_anuncia_pendientes(self):
        self.assertTrue(self._notice())
        self.order.state = "cancel"
        self.assertFalse(self._notice())
        self._type()
        self.order.state = "done"
        self.assertFalse(self._notice())

    def test_vista_muestra_aviso_sin_enlaces_y_con_chatter_nativo(self):
        view = self.env["repair.order"].get_view(
            view_id=self.env.ref("repair.view_repair_order_form").id, view_type="form"
        )
        root = etree.fromstring(view["arch"].encode())
        nodes = root.xpath("//div[@name='mc_aviso_cierre']")
        self.assertEqual(len(nodes), 1, "Falta la franja contextual")
        self.assertFalse(nodes[0].xpath(".//button | .//a"))
        self.assertEqual(nodes[0].get("invisible"), "not mc_aviso_cierre")
        self.assertEqual(len(root.xpath("//chatter")), 1)
        self.assertNotEqual(root.get("js_class"), "mc_rov_repair_guided_form")
