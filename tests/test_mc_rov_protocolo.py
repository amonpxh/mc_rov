from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

from odoo.addons.mc_rov.models.stock_lot import ROV_CATEG_PARAM


@tagged("post_install", "-at_install")
class ProtocoloCommon(TransactionCase):
    """Fixtures de los tests de protocolo. No declara tests.

    Necesita el árbol de categorías porque el protocolo lee es_un_rov del lote, y sin
    categoría ROV los lotes de prueba no lo estarían.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        categoria = cls.env["product.category"].create({"name": "ROV Test - Protocolos"})
        cls.env["ir.config_parameter"].sudo().set_param(ROV_CATEG_PARAM, str(categoria.id))

        cls.product = cls.env["product.product"].create(
            {"name": "ROV Test Protocolo", "tracking": "serial", "categ_id": categoria.id}
        )
        cls.empleado = cls.env["hr.employee"].create({"name": "Técnico de Prueba"})

    def setUp(self):
        super().setUp()
        self.lot = self.env["stock.lot"].create(
            {"name": "ROV-PROT-001", "product_id": self.product.id}
        )

    def _protocolo(self, **vals):
        return self.env["mc.rov.protocolo"].create(
            {
                "lot_id": self.lot.id,
                "responsable_id": self.empleado.id,
                **vals,
            }
        )

    def _corrida_completa(self, protocolo, **vals):
        """Una corrida que no impide confirmar."""
        return self.env["mc.rov.protocolo.corrida"].create(
            {
                "protocolo_id": protocolo.id,
                "umbilical": "equipo",
                "largo": 100.0,
                "alimentacion": "Generador",
                "tension_salida": 220,
                "esfuerzo_duracion": 1.5,
                "esfuerzo_resultado": "ok",
                **vals,
            }
        )

    def _responder_todo(self, protocolo, resultado="ok"):
        protocolo.chequeo_ids.write({"resultado": resultado})


@tagged("post_install", "-at_install")
class TestMcRovProtocolo(ProtocoloCommon):
    """Tests de la cabecera: secuencia, derivados y generación del checklist."""

    def test_el_protocolo_toma_su_numero_de_la_secuencia(self):
        self.assertTrue(self._protocolo().name.startswith("PROT/"))

    def test_el_protocolo_deriva_el_equipo_sin_guardar_contactos_propios(self):
        """Propietario y cliente son dos cosas distintas y ninguna vive acá."""
        protocolo = self._protocolo()

        self.assertEqual(protocolo.product_id, self.product)
        self.assertEqual(protocolo.propietario_id, self.lot.mc_propietario_id)
        self.assertFalse(protocolo.partner_id)

    def test_un_protocolo_de_recepcion_trae_su_checklist_generado(self):
        """Las líneas las pone el sistema: si las eligiera el técnico, no habría forma de
        distinguir "revisado y limpio" de "no se me ocurrió mirarlo"."""
        protocolo = self._protocolo(tipo="recepcion")

        self.assertTrue(protocolo.chequeo_ids)

    def test_fabricacion_no_trae_la_inspeccion_fisica(self):
        """La inspección física busca huellas de terceros. En un equipo recién armado por
        ellos mismos eso no significa nada, y generar quince líneas que hay que responder
        para poder confirmar sería puro ruido."""
        fabricacion = self._protocolo(tipo="fabricacion")
        recepcion = self._protocolo(tipo="recepcion")

        secciones_fab = set(fabricacion.chequeo_ids.mapped("seccion"))
        secciones_rec = set(recepcion.chequeo_ids.mapped("seccion"))

        self.assertNotIn("inspeccion_fisica", secciones_fab)
        self.assertIn("inspeccion_fisica", secciones_rec)

    def test_la_inspeccion_fisica_solo_recorre_los_componentes_marcados(self):
        """Sin es_inspeccionable, un chequeo por componente generaría una línea por cada
        entrada del catálogo — umbilical y sensor incluidos, que nadie revisa buscando
        sellos ajenos."""
        protocolo = self._protocolo(tipo="recepcion")

        inspeccion = protocolo.chequeo_ids.filtered(
            lambda linea: linea.seccion == "inspeccion_fisica"
        )
        componentes = inspeccion.mapped("componente_id")

        self.assertTrue(componentes)
        self.assertTrue(all(componentes.mapped("es_inspeccionable")))

    def test_cambiar_el_tipo_ajusta_el_checklist_sin_borrar_respuestas(self):
        """Cambiar de recepción a fabricación quita las líneas que ya no corresponden, pero
        nunca las que alguien contestó: el dato ya se levantó."""
        protocolo = self._protocolo(tipo="recepcion")
        inspeccion = protocolo.chequeo_ids.filtered(
            lambda linea: linea.seccion == "inspeccion_fisica"
        )
        respondida = inspeccion[0]
        respondida.resultado = "ok"

        protocolo.tipo = "fabricacion"

        self.assertIn(respondida, protocolo.chequeo_ids)
        sin_responder = inspeccion - respondida
        self.assertFalse(sin_responder.exists())


@tagged("post_install", "-at_install")
class TestMcRovProtocoloResultado(ProtocoloCommon):
    """Tests de `resultado`, que se deriva y no se decide."""

    def test_sin_hallazgos_ni_fallas_el_protocolo_esta_aprobado(self):
        protocolo = self._protocolo()
        self._corrida_completa(protocolo)
        self._responder_todo(protocolo)

        self.assertEqual(protocolo.resultado, "aprobado")

    def test_un_hallazgo_cualquiera_lo_deja_con_observaciones(self):
        protocolo = self._protocolo()
        self._corrida_completa(protocolo)
        self._responder_todo(protocolo)
        self.env["mc.rov.protocolo.hallazgo"].create(
            {
                "protocolo_id": protocolo.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
                "severidad": "informativo",
            }
        )

        self.assertEqual(protocolo.resultado, "aprobado_con_observaciones")

    def test_un_hallazgo_que_impide_operar_lo_rechaza(self):
        protocolo = self._protocolo()
        self._corrida_completa(protocolo)
        self._responder_todo(protocolo)
        self.env["mc.rov.protocolo.hallazgo"].create(
            {
                "protocolo_id": protocolo.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_no_responde").id,
                "severidad": "impide_operar",
            }
        )

        self.assertEqual(protocolo.resultado, "rechazado")

    def test_un_chequeo_fallado_rechaza_aunque_nadie_escriba_el_hallazgo(self):
        """El equipo no pasó, y eso no se compensa con que nadie haya explicado por qué."""
        protocolo = self._protocolo()
        self._corrida_completa(protocolo)
        self._responder_todo(protocolo)
        protocolo.chequeo_ids[0].resultado = "no_ok"

        self.assertEqual(protocolo.resultado, "rechazado")

    def test_un_esfuerzo_con_problemas_rechaza(self):
        protocolo = self._protocolo()
        self._corrida_completa(protocolo, esfuerzo_resultado="con_problemas")
        self._responder_todo(protocolo)

        self.assertEqual(protocolo.resultado, "rechazado")

    def test_no_lo_tiene_no_es_una_falla(self):
        """Un equipo sin joystick no está reprobado por no tenerlo."""
        protocolo = self._protocolo()
        self._corrida_completa(protocolo)
        self._responder_todo(protocolo, resultado="no_lo_tiene")

        self.assertEqual(protocolo.resultado, "aprobado")


@tagged("post_install", "-at_install")
class TestMcRovProtocoloConfirmacion(ProtocoloCommon):
    """Tests de lo que se exige para confirmar."""

    def test_sin_corridas_no_deja_confirmar(self):
        """La prueba de esfuerzo siempre se hace, así que un protocolo sin corridas dice
        que no se probó nada."""
        protocolo = self._protocolo()
        self._responder_todo(protocolo)

        with self.assertRaises(UserError):
            protocolo.action_confirmar()

    def test_con_chequeos_sin_responder_no_deja_confirmar(self):
        protocolo = self._protocolo()
        self._corrida_completa(protocolo)

        with self.assertRaises(UserError):
            protocolo.action_confirmar()

    def test_media_medicion_no_deja_confirmar(self):
        """Subida sin bajada parece un dato y no lo es."""
        protocolo = self._protocolo()
        self._corrida_completa(protocolo, subida=90.0)
        self._responder_todo(protocolo)

        with self.assertRaises(UserError):
            protocolo.action_confirmar()

    def test_un_esfuerzo_sin_duracion_no_deja_confirmar(self):
        """Cuánto aguantó es información distinta de si pasó."""
        protocolo = self._protocolo()
        self._corrida_completa(protocolo, esfuerzo_duracion=0.0)
        self._responder_todo(protocolo)

        with self.assertRaises(UserError):
            protocolo.action_confirmar()

    def test_un_protocolo_completo_se_confirma(self):
        protocolo = self._protocolo()
        self._corrida_completa(protocolo)
        self._responder_todo(protocolo)

        protocolo.action_confirmar()

        self.assertEqual(protocolo.estado, "confirmado")

    def test_el_mensaje_de_error_nombra_todo_lo_que_falta_de_una_vez(self):
        """Descubrir los faltantes de a uno, guardando entre medio, es la forma más segura
        de que el técnico abandone.

        Se comprueba sobre el mensaje que ve el usuario y no sobre el método interno: lo
        que importa es que enumere, no cómo lo calcula.
        """
        protocolo = self._protocolo()
        protocolo.responsable_id = False

        with self.assertRaises(UserError) as error:
            protocolo.action_confirmar()

        # El mensaje lista con viñetas; más de una significa que no se rindió en el primero.
        self.assertGreaterEqual(str(error.exception).count("·"), 2)

    def test_se_puede_volver_a_borrador(self):
        protocolo = self._protocolo()
        self._corrida_completa(protocolo)
        self._responder_todo(protocolo)
        protocolo.action_confirmar()

        protocolo.action_volver_a_borrador()

        self.assertEqual(protocolo.estado, "borrador")


@tagged("post_install", "-at_install")
class TestMcRovProtocoloLuces(ProtocoloCommon):
    """Tests de la comparación contra la ficha técnica del equipo."""

    def test_el_conteo_de_luces_se_suma_solo(self):
        protocolo = self._protocolo(luces_internas=2, luces_externas=4)

        self.assertEqual(protocolo.luces_total, 6)

    def test_avisa_cuando_el_conteo_no_cuadra_con_la_ficha(self):
        """Si el ROV debería tener seis luces y se contaron cuatro, el sistema lo dice sin
        que nadie tenga que acordarse de comparar."""
        self.lot.mc_cantidad_luces = 6
        protocolo = self._protocolo(luces_internas=2, luces_externas=2)

        self.assertTrue(protocolo.luces_difieren)

    def test_no_avisa_cuando_la_ficha_no_dice_cuantas_hay(self):
        """Sin referencia no hay comparación posible: la alerta se calla en vez de mentir."""
        self.lot.mc_cantidad_luces = 0
        protocolo = self._protocolo(luces_internas=2, luces_externas=2)

        self.assertFalse(protocolo.luces_difieren)


@tagged("post_install", "-at_install")
class TestMcRovProtocoloTrazabilidad(ProtocoloCommon):
    """Tests del circuito hallazgo → trabajo, que es lo que hace servible al modelo."""

    def test_una_linea_de_trabajo_apunta_al_hallazgo_que_resuelve(self):
        protocolo = self._protocolo()
        hallazgo = self.env["mc.rov.protocolo.hallazgo"].create(
            {
                "protocolo_id": protocolo.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
            }
        )
        orden = self.env["repair.order"].create(
            {"product_id": self.product.id, "lot_id": self.lot.id}
        )

        linea = self.env["mc.rov.linea.falla"].create(
            {
                "repair_id": orden.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "accion_id": self.env.ref("mc_rov.accion_reparacion").id,
                "hallazgo_origen_id": hallazgo.id,
                "responsable_id": self.empleado.id,
                "causa_raiz": "corrosion",
            }
        )

        self.assertEqual(linea.hallazgo_origen_id, hallazgo)
        self.assertEqual(linea.responsable_id, self.empleado)
        self.assertEqual(linea.causa_raiz, "corrosion")

    def test_el_hallazgo_sabe_de_que_equipo_es(self):
        """lot_id almacenado en la línea es lo que permite agregar hallazgos por equipo sin
        pasar por el protocolo en cada consulta."""
        protocolo = self._protocolo()
        hallazgo = self.env["mc.rov.protocolo.hallazgo"].create(
            {
                "protocolo_id": protocolo.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
            }
        )

        self.assertEqual(hallazgo.lot_id, self.lot)

    def test_el_equipo_acumula_su_historial_de_protocolos(self):
        """Dos protocolos del mismo equipo son la serie de tiempo: es lo que deja ver que
        el ancho de banda cayó entre una visita y la siguiente."""
        self._protocolo(tipo="recepcion", fecha=fields.Date.to_date("2026-01-15"))
        self._protocolo(tipo="entrega", fecha=fields.Date.to_date("2026-01-20"))

        self.assertEqual(len(self.lot.protocolo_ids), 2)
        self.assertEqual(self.lot.mc_protocolo_count, 2)
