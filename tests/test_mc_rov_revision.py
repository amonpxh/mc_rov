from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

from odoo.addons.mc_rov.models.stock_lot import ROV_CATEG_PARAM


@tagged("post_install", "-at_install")
class RevisionCommon(TransactionCase):
    """Fixtures de los tests de revision. No declara tests.

    Necesita el árbol de categorías porque la revisión lee es_un_rov del lote, y sin
    categoría ROV los lotes de prueba no lo estarían.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        categoria = cls.env["product.category"].create({"name": "ROV Test - Revisiones"})
        cls.env["ir.config_parameter"].sudo().set_param(ROV_CATEG_PARAM, str(categoria.id))

        cls.product = cls.env["product.product"].create(
            {"name": "ROV Test Revisión", "tracking": "serial", "categ_id": categoria.id}
        )
        cls.empleado = cls.env["hr.employee"].create({"name": "Técnico de Prueba"})

    def setUp(self):
        super().setUp()
        self.lot = self.env["stock.lot"].create(
            {"name": "ROV-PROT-001", "product_id": self.product.id}
        )

    def _revision(self, **vals):
        return self.env["mc.rov.revision"].create(
            {
                "lot_id": self.lot.id,
                "responsable_id": self.empleado.id,
                **vals,
            }
        )

    def _corrida_completa(self, revision, **vals):
        """Una corrida que no impide confirmar."""
        return self.env["mc.rov.revision.corrida"].create(
            {
                "revision_id": revision.id,
                "umbilical": "equipo",
                "largo": 100.0,
                "alimentacion": "Generador",
                "tension_salida": 220,
                "esfuerzo_duracion": 1.5,
                "esfuerzo_resultado": "ok",
                **vals,
            }
        )

    def _responder_todo(self, revision, resultado="ok"):
        """Responde el checklist. Los sellos van aparte, para poder probarlos solos."""
        revision.chequeo_ids.write({"resultado": resultado})

    def _responder_sellos(self, revision, estado="intacto"):
        revision.inspeccion_ids.write({"estado_sello": estado})


@tagged("post_install", "-at_install")
class TestMcRovRevision(RevisionCommon):
    """Tests de la cabecera: secuencia, derivados y generación del checklist."""

    def test_el_revision_toma_su_numero_de_la_secuencia(self):
        self.assertTrue(self._revision().name.startswith("REV/"))

    def test_el_revision_deriva_el_equipo_sin_guardar_contactos_propios(self):
        """Propietario y cliente son dos cosas distintas y ninguna vive acá."""
        revision = self._revision()

        self.assertEqual(revision.product_id, self.product)
        self.assertEqual(revision.propietario_id, self.lot.mc_propietario_id)
        self.assertFalse(revision.partner_id)

    def test_un_revision_de_recepcion_trae_su_checklist_generado(self):
        """Las líneas las pone el sistema: si las eligiera el técnico, no habría forma de
        distinguir "revisado y limpio" de "no se me ocurrió mirarlo"."""
        revision = self._revision(tipo="recepcion")

        self.assertTrue(revision.chequeo_ids)

    def test_fabricacion_no_trae_la_inspeccion_fisica(self):
        """La inspección física busca huellas de terceros. En un equipo recién armado por
        ellos mismos eso no significa nada, y generar quince líneas que hay que responder
        para poder confirmar sería puro ruido."""
        fabricacion = self._revision(tipo="fabricacion")
        recepcion = self._revision(tipo="recepcion")

        secciones_fab = set(fabricacion.chequeo_ids.mapped("seccion"))
        secciones_rec = set(recepcion.chequeo_ids.mapped("seccion"))

        self.assertNotIn("inspeccion_fisica", secciones_fab)
        self.assertIn("inspeccion_fisica", secciones_rec)

    def test_la_inspeccion_fisica_solo_recorre_los_componentes_marcados(self):
        """Sin es_inspeccionable, un chequeo por componente generaría una línea por cada
        entrada del catálogo — umbilical y sensor incluidos, que nadie revisa buscando
        sellos ajenos."""
        revision = self._revision(tipo="recepcion")

        inspeccion = revision.chequeo_ids.filtered(
            lambda linea: linea.seccion == "inspeccion_fisica"
        )
        componentes = inspeccion.mapped("componente_id")

        self.assertTrue(componentes)
        self.assertTrue(all(componentes.mapped("es_inspeccionable")))

    def test_cambiar_el_tipo_ajusta_el_checklist_sin_borrar_respuestas(self):
        """Cambiar de recepción a fabricación quita las líneas que ya no corresponden, pero
        nunca las que alguien contestó: el dato ya se levantó."""
        revision = self._revision(tipo="recepcion")
        inspeccion = revision.chequeo_ids.filtered(
            lambda linea: linea.seccion == "inspeccion_fisica"
        )
        respondida = inspeccion[0]
        respondida.resultado = "ok"

        revision.tipo = "fabricacion"

        self.assertIn(respondida, revision.chequeo_ids)
        sin_responder = inspeccion - respondida
        self.assertFalse(sin_responder.exists())


@tagged("post_install", "-at_install")
class TestMcRovRevisionResultado(RevisionCommon):
    """Tests de `resultado`, que se deriva y no se decide."""

    def test_sin_hallazgos_ni_fallas_el_revision_esta_aprobado(self):
        revision = self._revision()
        self._corrida_completa(revision)
        self._responder_todo(revision)

        self.assertEqual(revision.resultado, "aprobado")

    def test_un_hallazgo_cualquiera_lo_deja_con_observaciones(self):
        revision = self._revision()
        self._corrida_completa(revision)
        self._responder_todo(revision)
        self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
                "severidad": "informativo",
            }
        )

        self.assertEqual(revision.resultado, "aprobado_con_observaciones")

    def test_un_hallazgo_que_impide_operar_lo_rechaza(self):
        revision = self._revision()
        self._corrida_completa(revision)
        self._responder_todo(revision)
        self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_no_responde").id,
                "severidad": "impide_operar",
            }
        )

        self.assertEqual(revision.resultado, "rechazado")

    def test_un_chequeo_fallado_rechaza_aunque_nadie_escriba_el_hallazgo(self):
        """El equipo no pasó, y eso no se compensa con que nadie haya explicado por qué."""
        revision = self._revision()
        self._corrida_completa(revision)
        self._responder_todo(revision)
        revision.chequeo_ids[0].resultado = "no_ok"

        self.assertEqual(revision.resultado, "rechazado")

    def test_un_esfuerzo_con_problemas_rechaza(self):
        revision = self._revision()
        self._corrida_completa(revision, esfuerzo_resultado="con_problemas")
        self._responder_todo(revision)

        self.assertEqual(revision.resultado, "rechazado")

    def test_no_lo_tiene_no_es_una_falla(self):
        """Un equipo sin joystick no está reprobado por no tenerlo."""
        revision = self._revision()
        self._corrida_completa(revision)
        self._responder_todo(revision, resultado="no_lo_tiene")

        self.assertEqual(revision.resultado, "aprobado")


@tagged("post_install", "-at_install")
class TestMcRovRevisionConfirmacion(RevisionCommon):
    """Tests de lo que se exige para confirmar."""

    def test_sin_corridas_no_deja_confirmar(self):
        """La prueba de esfuerzo siempre se hace, así que una revisión sin corridas dice
        que no se probó nada."""
        revision = self._revision()
        self._responder_todo(revision)

        with self.assertRaises(UserError):
            revision.action_confirmar()

    def test_con_chequeos_sin_responder_no_deja_confirmar(self):
        revision = self._revision()
        self._corrida_completa(revision)

        with self.assertRaises(UserError):
            revision.action_confirmar()

    def test_media_medicion_no_deja_confirmar(self):
        """Subida sin bajada parece un dato y no lo es."""
        revision = self._revision()
        self._corrida_completa(revision, subida=90.0)
        self._responder_todo(revision)

        with self.assertRaises(UserError):
            revision.action_confirmar()

    def test_un_esfuerzo_sin_duracion_no_deja_confirmar(self):
        """Cuánto aguantó es información distinta de si pasó."""
        revision = self._revision()
        self._corrida_completa(revision, esfuerzo_duracion=0.0)
        self._responder_todo(revision)

        with self.assertRaises(UserError):
            revision.action_confirmar()

    def test_un_revision_completo_se_confirma(self):
        revision = self._revision()
        self._corrida_completa(revision)
        self._responder_todo(revision)
        self._responder_sellos(revision)

        revision.action_confirmar()

        self.assertEqual(revision.estado, "confirmado")

    def test_el_mensaje_de_error_nombra_todo_lo_que_falta_de_una_vez(self):
        """Descubrir los faltantes de a uno, guardando entre medio, es la forma más segura
        de que el técnico abandone.

        Se comprueba sobre el mensaje que ve el usuario y no sobre el método interno: lo
        que importa es que enumere, no cómo lo calcula.
        """
        revision = self._revision()
        revision.responsable_id = False

        with self.assertRaises(UserError) as error:
            revision.action_confirmar()

        # El mensaje lista con viñetas; más de una significa que no se rindió en el primero.
        self.assertGreaterEqual(str(error.exception).count("·"), 2)

    def test_se_puede_volver_a_borrador(self):
        revision = self._revision()
        self._corrida_completa(revision)
        self._responder_todo(revision)
        self._responder_sellos(revision)
        revision.action_confirmar()

        revision.action_volver_a_borrador()

        self.assertEqual(revision.estado, "borrador")


@tagged("post_install", "-at_install")
class TestMcRovRevisionLuces(RevisionCommon):
    """Tests de la comparación contra la ficha técnica del equipo."""

    def test_el_conteo_de_luces_se_suma_solo(self):
        revision = self._revision(luces_internas=2, luces_externas=4)

        self.assertEqual(revision.luces_total, 6)

    def test_avisa_cuando_el_conteo_no_cuadra_con_la_ficha(self):
        """Si el ROV debería tener seis luces y se contaron cuatro, el sistema lo dice sin
        que nadie tenga que acordarse de comparar."""
        self.lot.mc_cantidad_luces = 6
        revision = self._revision(luces_internas=2, luces_externas=2)

        self.assertTrue(revision.luces_difieren)

    def test_no_avisa_cuando_la_ficha_no_dice_cuantas_hay(self):
        """Sin referencia no hay comparación posible: la alerta se calla en vez de mentir."""
        self.lot.mc_cantidad_luces = 0
        revision = self._revision(luces_internas=2, luces_externas=2)

        self.assertFalse(revision.luces_difieren)


@tagged("post_install", "-at_install")
class TestMcRovRevisionTrazabilidad(RevisionCommon):
    """Tests del circuito hallazgo → trabajo, que es lo que hace servible al modelo."""

    def test_una_linea_de_trabajo_apunta_al_hallazgo_que_resuelve(self):
        revision = self._revision()
        hallazgo = self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
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
        pasar por la revisión en cada consulta."""
        revision = self._revision()
        hallazgo = self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
            }
        )

        self.assertEqual(hallazgo.lot_id, self.lot)

    def test_el_equipo_acumula_su_historial_de_revisiones(self):
        """Dos revisiones del mismo equipo son la serie de tiempo: es lo que deja ver que
        el ancho de banda cayó entre una visita y la siguiente."""
        self._revision(tipo="recepcion", fecha=fields.Date.to_date("2026-01-15"))
        self._revision(tipo="entrega", fecha=fields.Date.to_date("2026-01-20"))

        self.assertEqual(len(self.lot.revision_ids), 2)
        self.assertEqual(self.lot.mc_revision_count, 2)


@tagged("post_install", "-at_install")
class TestMcRovRevisionSellos(RevisionCommon):
    """Tests de la inspección de sellos, que reemplazó a tres casillas independientes."""

    def test_la_recepcion_trae_una_fila_por_componente_sellado(self):
        revision = self._revision(tipo="recepcion")

        self.assertTrue(revision.inspeccion_ids)
        componentes = revision.inspeccion_ids.mapped("componente_id")
        self.assertTrue(all(componentes.mapped("es_inspeccionable")))

    def test_fabricacion_no_lleva_inspeccion_de_sellos(self):
        """En un equipo recién armado no hay sello previo que mirar."""
        self.assertFalse(self._revision(tipo="fabricacion").inspeccion_ids)

    def test_un_sello_roto_en_recepcion_es_manipulacion_externa(self):
        """El taller nunca rompe un sello sin registrarlo, y sus roturas ocurren durante el
        trabajo — después de la recepción. Así que roto al recibir no tiene ambigüedad."""
        revision = self._revision(tipo="recepcion")
        linea = revision.inspeccion_ids[0]

        linea.estado_sello = "roto"

        self.assertTrue(linea.manipulacion_externa)

    def test_un_sello_roto_en_entrega_no_lo_es(self):
        """En entrega los sellos los pone el propio taller."""
        revision = self._revision(tipo="entrega")
        linea = revision.inspeccion_ids[0]

        linea.estado_sello = "roto"

        self.assertFalse(linea.manipulacion_externa)

    def test_un_sello_intacto_no_es_manipulacion(self):
        revision = self._revision(tipo="recepcion")
        linea = revision.inspeccion_ids[0]

        linea.estado_sello = "intacto"

        self.assertFalse(linea.manipulacion_externa)

    def test_no_deja_confirmar_con_sellos_sin_revisar(self):
        revision = self._revision(tipo="recepcion")
        self._corrida_completa(revision)
        self._responder_todo(revision)

        with self.assertRaises(UserError):
            revision.action_confirmar()

    def test_confirma_cuando_los_sellos_estan_revisados(self):
        revision = self._revision(tipo="recepcion")
        self._corrida_completa(revision)
        self._responder_todo(revision)
        revision.inspeccion_ids.write({"estado_sello": "intacto"})

        revision.action_confirmar()

        self.assertEqual(revision.estado, "confirmado")


@tagged("post_install", "-at_install")
class TestMcRovRevisionAutomatica(RevisionCommon):
    """Tests de la revisión de recepción que se abre sola al entrar el equipo al taller."""

    def _orden(self, **vals):
        return self.env["repair.order"].create(
            {"product_id": self.product.id, "lot_id": self.lot.id, **vals}
        )

    def _recepciones(self, orden):
        return self.env["mc.rov.revision"].search(
            [("repair_id", "=", orden.id), ("tipo", "=", "recepcion")]
        )

    def test_una_orden_en_borrador_no_abre_revision(self):
        """Un borrador es una cotización: el equipo puede no haber llegado."""
        self.assertFalse(self._recepciones(self._orden()))

    def test_confirmar_la_orden_abre_la_revision_de_recepcion(self):
        """Siempre ocurre, así que no puede depender de que alguien apriete un botón."""
        orden = self._orden()

        orden.state = "confirmed"

        self.assertEqual(len(self._recepciones(orden)), 1)

    def test_no_se_duplica_al_avanzar_de_estado(self):
        orden = self._orden()

        orden.state = "confirmed"
        orden.state = "under_repair"

        self.assertEqual(len(self._recepciones(orden)), 1)

    def test_cancelar_no_abre_revision(self):
        orden = self._orden()

        orden.state = "cancel"

        self.assertFalse(self._recepciones(orden))

    def test_una_orden_sin_rov_no_abre_revision(self):
        """Una reparación de componente no lleva revisión técnica."""
        product_ajeno = self.env["product.product"].create(
            {"name": "Componente Test Rev", "tracking": "serial"}
        )
        lot_ajeno = self.env["stock.lot"].create(
            {"name": "COMP-REV-001", "product_id": product_ajeno.id}
        )
        orden = self.env["repair.order"].create(
            {"product_id": product_ajeno.id, "lot_id": lot_ajeno.id}
        )

        orden.state = "confirmed"

        self.assertFalse(self._recepciones(orden))
