from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

from odoo.addons.mc_rov.models.stock_lot import (
    CICLO_MANTENCION_PARAM,
    ROV_CATEG_PARAM,
)

# Una ficha técnica que sí cuenta como levantada. Los tests parten de aquí y le sacan una
# cosa por vez, para que cada caso diga exactamente qué la deja incompleta.
FICHA_COMPLETA = {
    "mc_chasis": "Inox",
    "mc_modelo_motores": "T200",
    "mc_n_motores": 6,
    "mc_posicion_motores": "Vectorial",
    "mc_peso_consola": 12.0,
    "mc_peso_rov": 25.0,
    "mc_sensor_presion": "30 bar",
    "mc_tarjeta_comunicacion_rov": "V50",
    "mc_tarjeta_comunicacion_consola": "V50",
    "mc_version_controlador": "1.2.0",
    "mc_version_ardusub": "4.1.0",
    "mc_version_software": "4.2.6",
    "mc_cantidad_luces": 4,
    "mc_tiene_horometro": "si",
}


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

    def test_un_equipo_de_baja_no_tiene_reloj(self):
        """Un equipo dado de baja seguía apareciendo en la lista de vencidos.

        O sea que comercial habría llamado a un cliente a ofrecerle la mantención de un
        equipo que ya no existe.
        """
        self.lot.mc_fecha_puesta_servicio = fields.Date.to_date("2026-03-15")
        self.assertTrue(self.lot.proxima_mantencion)

        self.lot.dar_de_baja(fields.Date.today(), "Chasis irrecuperable")

        self.assertFalse(self.lot.proxima_mantencion)


@tagged("post_install", "-at_install")
class StockLotPropiedadCommon(TransactionCase):
    """Fixtures de los tests de propiedad. No declara tests.

    A diferencia de StockLotOrdenesCommon, aquí sí hace falta el árbol de categorías:
    el historial de propiedad solo se abre para equipos con es_un_rov encendido, y sin
    categoría ROV los lotes de prueba no lo estarían.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        categoria = cls.env["product.category"].create({"name": "ROV Test - Vehiculos"})
        cls.env["ir.config_parameter"].sudo().set_param(ROV_CATEG_PARAM, str(categoria.id))

        cls.product = cls.env["product.product"].create(
            {
                "name": "ROV Test Propiedad",
                "tracking": "serial",
                "categ_id": categoria.id,
                "rent_ok": True,
            }
        )
        # Fuera de la rama ROV: sirve para comprobar que a los componentes no se les
        # abre historial.
        cls.product_ajeno = cls.env["product.product"].create(
            {
                "name": "Componente Test",
                "tracking": "serial",
            }
        )

        cls.empresa = cls.env.company.partner_id
        cls.cliente = cls.env["res.partner"].create({"name": "Salmones Test SpA"})
        cls.otro_cliente = cls.env["res.partner"].create({"name": "Pesquera Test Ltda"})

    def setUp(self):
        super().setUp()
        # Lote nuevo por cada test para garantizar aislamiento
        self.lot = self.env["stock.lot"].create(
            {
                "name": "ROV-PROP-001",
                "product_id": self.product.id,
            }
        )

    def _periodos(self):
        """Períodos de propiedad del equipo, del más nuevo al más antiguo."""
        return self.lot.mc_propietario_historial_ids


@tagged("post_install", "-at_install")
class TestStockLotPropiedad(StockLotPropiedadCommon):
    """Tests de mc_propietario_id y del historial que se escribe solo."""

    def test_un_rov_nuevo_queda_a_nombre_de_la_empresa(self):
        """Vacío no puede significar "es nuestro": se confundiría con no llenado."""
        self.assertEqual(self.lot.mc_propietario_id, self.empresa)

    def test_un_rov_nuevo_abre_su_primer_periodo(self):
        periodos = self._periodos()
        self.assertEqual(len(periodos), 1)
        self.assertEqual(periodos.partner_id, self.empresa)
        self.assertFalse(periodos.fecha_hasta)

    def test_traspasar_cierra_el_periodo_anterior_y_abre_uno_nuevo(self):
        """Se comprueba cuál período quedó abierto, no en qué posición vino.

        Dentro de la misma transacción el one2many llega en el orden en que se fue
        llenando la caché, no en el _order del modelo, así que apoyarse en el índice
        probaría un detalle de la caché en vez de la regla de negocio.
        """
        self.lot.mc_propietario_id = self.cliente

        periodos = self._periodos()
        self.assertEqual(len(periodos), 2)

        vigente = periodos.filtered(lambda periodo: not periodo.fecha_hasta)
        cerrado = periodos - vigente

        self.assertEqual(vigente.partner_id, self.cliente)
        self.assertEqual(cerrado.partner_id, self.empresa)
        self.assertEqual(cerrado.fecha_hasta, fields.Date.today())

    def test_reescribir_el_mismo_propietario_no_ensucia_el_historial(self):
        """Guardar el formulario sin cambiar de dueño no es un traspaso."""
        self.lot.mc_propietario_id = self.empresa

        self.assertEqual(len(self._periodos()), 1)

    def test_solo_queda_un_periodo_abierto_tras_varios_traspasos(self):
        self.lot.mc_propietario_id = self.cliente
        self.lot.mc_propietario_id = self.otro_cliente

        abiertos = self._periodos().filtered(lambda periodo: not periodo.fecha_hasta)
        self.assertEqual(len(abiertos), 1)
        self.assertEqual(abiertos.partner_id, self.otro_cliente)

    def test_un_lote_que_no_es_rov_no_abre_historial(self):
        """Los lotes de componentes llenarían la tabla de filas que nadie consulta."""
        componente = self.env["stock.lot"].create(
            {
                "name": "CMP-TEST-001",
                "product_id": self.product_ajeno.id,
            }
        )

        self.assertFalse(componente.mc_propietario_historial_ids)


@tagged("post_install", "-at_install")
class TestStockLotEstadoComercial(StockLotPropiedadCommon):
    """Tests de mc_estado_comercial, que se deriva de propiedad, arriendos y baja."""

    def _linea_arriendo(self, retirados=None, devueltos=None):
        """Crea una línea de arriendo con los equipos retirados y devueltos dados."""
        vacio = self.env["stock.lot"]
        orden = self.env["sale.order"].create({"partner_id": self.cliente.id})
        return self.env["sale.order.line"].create(
            {
                "order_id": orden.id,
                "product_id": self.product.id,
                "is_rental": True,
                "pickedup_lot_ids": [(6, 0, (retirados or vacio).ids)],
                "returned_lot_ids": [(6, 0, (devueltos or vacio).ids)],
            }
        )

    def test_un_rov_de_la_empresa_esta_disponible(self):
        self.assertEqual(self.lot.mc_estado_comercial, "Disponible")

    def test_un_rov_a_nombre_de_un_cliente_esta_vendido(self):
        self.lot.mc_propietario_id = self.cliente

        self.assertEqual(self.lot.mc_estado_comercial, "Vendido")

    def test_un_equipo_retirado_en_arriendo_dice_en_arriendo(self):
        self._linea_arriendo(retirados=self.lot)

        self.assertEqual(self.lot.mc_estado_comercial, "En arriendo")

    def test_un_equipo_devuelto_vuelve_a_disponible(self):
        """Cubre el override de sale.order.line: sin él el equipo seguiría arrendado."""
        linea = self._linea_arriendo(retirados=self.lot)

        linea.returned_lot_ids = [(6, 0, self.lot.ids)]

        self.assertEqual(self.lot.mc_estado_comercial, "Disponible")

    def test_la_baja_gana_sobre_vendido(self):
        """Un equipo dado de baja lo está aunque siga a nombre de un cliente."""
        self.lot.mc_propietario_id = self.cliente

        self.lot.dar_de_baja(fields.Date.today(), "Chasis irrecuperable")

        self.assertEqual(self.lot.mc_estado_comercial, "Baja")

    def test_dar_de_baja_guarda_fecha_y_motivo(self):
        self.lot.dar_de_baja(fields.Date.to_date("2026-02-10"), "Inundación del e-pod")

        self.assertEqual(self.lot.mc_fecha_baja, fields.Date.to_date("2026-02-10"))
        self.assertEqual(self.lot.mc_motivo_baja, "Inundación del e-pod")

    def test_reactivar_devuelve_el_equipo_a_su_estado_anterior(self):
        """Las bajas se equivocan, y revertirlas no debe perder el estado real."""
        self.lot.mc_propietario_id = self.cliente
        self.lot.dar_de_baja(fields.Date.today(), "Se dio por perdido")

        self.lot.reactivar()

        self.assertFalse(self.lot.mc_fecha_baja)
        self.assertEqual(self.lot.mc_estado_comercial, "Vendido")


@tagged("post_install", "-at_install")
class TestStockLotTraspasoDesdeOrden(StockLotPropiedadCommon):
    """Tests del traspaso que se detecta cuando el equipo llega al taller.

    Nadie avisa cuando un cliente revende su ROV: el síntoma es que el equipo vuelve a
    nombre de otro contacto, y de ahí sale el traspaso.
    """

    def _orden(self, **vals):
        return self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "lot_id": self.lot.id,
                **vals,
            }
        )

    def test_el_aviso_se_enciende_cuando_el_cliente_no_es_el_propietario(self):
        orden = self._orden(partner_id=self.cliente.id)

        self.assertTrue(orden.mc_propietario_difiere)

    def test_el_aviso_se_apaga_cuando_coinciden(self):
        orden = self._orden(partner_id=self.empresa.id)

        self.assertFalse(orden.mc_propietario_difiere)

    def test_traspasar_desde_la_orden_deja_el_equipo_a_nombre_del_cliente(self):
        orden = self._orden(partner_id=self.cliente.id)

        orden.action_actualizar_propietario_lote()

        self.assertEqual(self.lot.mc_propietario_id, self.cliente)
        self.assertFalse(orden.mc_propietario_difiere)

    def test_el_traspaso_queda_anotado_con_la_orden_que_lo_detecto(self):
        """El origen distingue una reventa detectada de una corrección a mano."""
        orden = self._orden(partner_id=self.cliente.id)

        orden.action_actualizar_propietario_lote()

        vigente = self.lot.mc_propietario_historial_ids.filtered(
            lambda periodo: not periodo.fecha_hasta
        )
        self.assertEqual(vigente.repair_id, orden)


@tagged("post_install", "-at_install")
class TestMcRovBajaWizard(StockLotPropiedadCommon):
    """Tests del asistente de baja, que es la única vía de entrada desde la interfaz."""

    def _asistente(self):
        return self.env["mc.rov.baja.wizard"].with_context(active_id=self.lot.id).create({})

    def test_el_asistente_toma_el_equipo_del_contexto(self):
        self.assertEqual(self._asistente().lot_id, self.lot)

    def test_dar_de_baja_desde_el_asistente_guarda_fecha_y_motivo(self):
        asistente = self._asistente()
        asistente.write(
            {
                "fecha": fields.Date.to_date("2026-02-10"),
                "motivo": "Inundación del e-pod",
            }
        )

        asistente.action_dar_de_baja()

        self.assertEqual(self.lot.mc_fecha_baja, fields.Date.to_date("2026-02-10"))
        self.assertEqual(self.lot.mc_motivo_baja, "Inundación del e-pod")
        self.assertEqual(self.lot.mc_estado_comercial, "Baja")

    def test_sin_motivo_no_deja_dar_de_baja(self):
        """La obligatoriedad se declara en la vista, pero eso no protege del RPC."""
        with self.assertRaises(UserError):
            self._asistente().action_dar_de_baja()

    def test_un_motivo_de_solo_espacios_tampoco_sirve(self):
        asistente = self._asistente()
        asistente.motivo = "   "

        with self.assertRaises(UserError):
            asistente.action_dar_de_baja()

        self.assertFalse(self.lot.mc_fecha_baja)

    def test_el_asistente_reactiva_un_equipo_de_baja(self):
        self.lot.dar_de_baja(fields.Date.today(), "Se dio por perdido")

        self._asistente().action_reactivar()

        self.assertFalse(self.lot.mc_fecha_baja)
        self.assertFalse(self.lot.mc_motivo_baja)
        self.assertEqual(self.lot.mc_estado_comercial, "Disponible")


@tagged("post_install", "-at_install")
class TestStockLotFichaCompleta(StockLotPropiedadCommon):
    """Tests de mc_ficha_completa, el indicador de ficha técnica levantada."""

    def _completar(self, **cambios):
        """Deja la ficha completa y luego aplica los cambios del caso.

        Los dos catálogos se resuelven aquí y no en FICHA_COMPLETA porque env.ref necesita
        un entorno, y el diccionario es de módulo.
        """
        catalogos = {
            "mc_controlador_vuelo": self.env.ref("mc_rov.ctrl_navigator").id,
            "mc_software_superficie": self.env.ref("mc_rov.soft_qgroundcontrol").id,
        }
        self.lot.write({**FICHA_COMPLETA, **catalogos, **cambios})
        return self.lot

    def test_una_serie_recien_creada_tiene_la_ficha_incompleta(self):
        self.assertFalse(self.lot.mc_ficha_completa)

    def test_con_todos_los_datos_la_ficha_esta_completa(self):
        self.assertTrue(self._completar().mc_ficha_completa)

    def test_un_campo_vacio_deja_la_ficha_incompleta(self):
        self.assertFalse(self._completar(mc_chasis=False).mc_ficha_completa)

    def test_un_catalogo_sin_elegir_deja_la_ficha_incompleta(self):
        """Un Many2one vacío se comprueba igual que un Selection vacío: basta con que no
        esté puesto."""
        self.assertFalse(self._completar(mc_software_superficie=False).mc_ficha_completa)

    def test_los_faltantes_nombran_el_numerico_en_cero(self):
        """Es la razón de ser de mc_ficha_faltantes.

        El navegador rechaza guardar con un numérico en cero pero no lo pinta de rojo, así
        que el usuario ve un guardado que falla sin causa visible. Nombrar el campo es más
        confiable que pelear con el resaltado de Odoo.
        """
        lot = self._completar(mc_n_motores=0)

        self.assertIn("N° motores", lot.mc_ficha_faltantes)

    def test_los_faltantes_incluyen_la_cantidad_de_luces(self):
        """El segundo numérico, y el que la ficha de reparación lee para comparar.

        Hasta 19.0.7.0.1 este campo vivía en Periféricos, así que bloqueaba el guardado
        desde otra pestaña sin que a nadie se le ocurriera ir a mirar allá. Ya está en
        Especificaciones con el resto, pero el caso se conserva: sigue siendo un conteo que
        en cero no significa "cero luces" sino "nadie lo llenó".
        """
        lot = self._completar(mc_cantidad_luces=0)

        self.assertIn("Cantidad de luces", lot.mc_ficha_faltantes)

    def test_una_ficha_completa_no_reporta_faltantes(self):
        self.assertFalse(self._completar().mc_ficha_faltantes)

    def test_cero_motores_deja_la_ficha_incompleta(self):
        """En Odoo un Integer nunca queda vacío: se lee como 0.

        Por eso el numérico se comprueba con > 0 y no con "está lleno". Un ROV con cero
        motores no existe, así que el cero es exactamente la señal de que nadie lo llenó
        —y es lo que entra por importación o por código, donde el required de la vista no
        alcanza.
        """
        self.assertFalse(self._completar(mc_n_motores=0).mc_ficha_completa)

    def test_un_peso_en_cero_deja_la_ficha_incompleta(self):
        self.assertFalse(self._completar(mc_peso_rov=0.0).mc_ficha_completa)

    def test_una_version_de_solo_espacios_deja_la_ficha_incompleta(self):
        self.assertFalse(self._completar(mc_version_ardusub="   ").mc_ficha_completa)

    def test_un_lote_que_no_es_rov_nunca_tiene_la_ficha_completa(self):
        """Y por eso el filtro de pendientes exige es_un_rov en su dominio.

        Un lote de componentes no tiene ninguno de estos datos ni va a tenerlos: sin esa
        condición, la lista de fichas por levantar traería miles de filas que nadie puede
        completar.
        """
        componente = self.env["stock.lot"].create(
            {"name": "COMP-FICHA-001", "product_id": self.product_ajeno.id}
        )
        componente.write(
            {
                **FICHA_COMPLETA,
                "mc_controlador_vuelo": self.env.ref("mc_rov.ctrl_navigator").id,
                "mc_software_superficie": self.env.ref("mc_rov.soft_qgroundcontrol").id,
            }
        )

        self.assertFalse(componente.es_un_rov)
        self.assertFalse(componente.mc_ficha_completa)
