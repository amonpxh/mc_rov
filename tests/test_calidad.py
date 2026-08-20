from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class CalidadCommon(TransactionCase):
    """Fixtures de los puentes a Calidad. No declara tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.producto = cls.env["product.product"].create(
            {"name": "ROV MC-300 Test", "tracking": "serial"}
        )
        cls.plantilla = cls.producto.product_tmpl_id
        cls.equipo = cls.env["stock.lot"].create(
            {"name": "SN-CALIDAD-1", "product_id": cls.producto.id}
        )
        cls.team = cls.env["quality.alert.team"].search([], limit=1) or cls.env[
            "quality.alert.team"
        ].create({"name": "Equipo de calidad test"})

        # Cuál de las cuatro etapas es la de cierre es dato, no código: se busca por el
        # booleano `done` en vez de comparar contra el nombre "Resuelto", que es
        # traducible y editable desde la interfaz.
        cls.etapa_cerrada = cls.env["quality.alert.stage"].search(
            [("done", "=", True)], limit=1
        ) or cls.env["quality.alert.stage"].create({"name": "Cerrada (test)", "done": True})
        cls.etapa_abierta = cls.env["quality.alert.stage"].search(
            [("done", "=", False)], limit=1
        ) or cls.env["quality.alert.stage"].create({"name": "Nueva (test)"})

    def _chequeo(self, **vals):
        return self.env["quality.check"].create(
            {"product_id": self.producto.id, "team_id": self.team.id, **vals}
        )

    def _leccion(self, preventiva="Se cambió el o-ring a Viton en todos los MC-300", **vals):
        """Una alerta cerrada y con acción preventiva escrita: eso es una lección."""
        return self.env["quality.alert"].create(
            {
                "product_tmpl_id": self.plantilla.id,
                "team_id": self.team.id,
                "stage_id": self.etapa_cerrada.id,
                "action_preventive": f"<p>{preventiva}</p>",
                **vals,
            }
        )


class TestAlertaAutomatica(CalidadCommon):
    """Fallar un chequeo crea la lección sola (§ 6.1.4 del diseño)."""

    def test_fallar_crea_alerta(self):
        chequeo = self._chequeo()
        chequeo.do_fail()

        self.assertEqual(len(chequeo.alert_ids), 1, "el fallo tiene que dejar una alerta")
        alerta = chequeo.alert_ids
        self.assertEqual(alerta.check_id, chequeo)
        self.assertEqual(alerta.product_tmpl_id, self.plantilla)

    def test_la_alerta_nace_sin_titulo(self):
        """A medio llenar a propósito: una deuda evidente en la lista se salda."""
        chequeo = self._chequeo()
        chequeo.do_fail()
        self.assertFalse(chequeo.alert_ids.title)

    def test_la_alerta_nace_sin_cerrar(self):
        chequeo = self._chequeo()
        chequeo.do_fail()
        self.assertFalse(
            chequeo.alert_ids.stage_id.done,
            "una lección recién abierta no puede nacer resuelta",
        )

    def test_aprobar_no_crea_nada(self):
        chequeo = self._chequeo()
        chequeo.do_pass()
        self.assertFalse(chequeo.alert_ids)

    def test_fallar_dos_veces_no_duplica(self):
        """El segundo intento entra al chatter de la primera, no en una alerta nueva.

        Es lo que convierte a la alerta en el historial de intentos: el chequeo pisa su
        propio estado al volver a aprobarse, así que sin esto el fallo desaparece.
        """
        chequeo = self._chequeo()
        chequeo.do_fail()
        alerta = chequeo.alert_ids
        mensajes_antes = len(alerta.message_ids)

        chequeo.do_pass()
        chequeo.do_fail()

        self.assertEqual(chequeo.alert_ids, alerta, "no debe aparecer una segunda alerta")
        self.assertGreater(
            len(alerta.message_ids), mensajes_antes, "el reintento tiene que quedar anotado"
        )

    def test_una_alerta_cerrada_no_se_reabre(self):
        """Un fallo nuevo sobre una lección ya aprendida merece su propia alerta."""
        chequeo = self._chequeo()
        chequeo.do_fail()
        chequeo.alert_ids.stage_id = self.etapa_cerrada

        chequeo.do_pass()
        chequeo.do_fail()

        self.assertEqual(len(chequeo.alert_ids), 2)

    def test_la_alerta_hereda_el_trabajo_que_la_origino(self):
        """Sin esto la alerta solo existe en la app de Calidad, adonde nadie entra."""
        orden = self.env["repair.order"].create({"product_id": self.producto.id})
        chequeo = self._chequeo(repair_id=orden.id)
        chequeo.do_fail()

        self.assertEqual(chequeo.alert_ids.repair_id, orden)
        self.assertIn(chequeo.alert_ids, orden.quality_alert_ids)


class TestAlcanceDeLaAlerta(CalidadCommon):
    """`lot_ids` se llena al terminar la orden, no al crear la alerta (§ 6.1.5)."""

    def setUp(self):
        super().setUp()
        self.mo = self.env["mrp.production"].create(
            {"product_id": self.producto.id, "product_qty": 1}
        )

    def test_sella_el_numero_de_serie_recien_nacido(self):
        alerta = self.env["quality.alert"].create(
            {
                "product_tmpl_id": self.plantilla.id,
                "team_id": self.team.id,
                "production_id": self.mo.id,
            }
        )
        self.assertFalse(alerta.lot_ids, "al fallar el chequeo todavía no hay serie")

        self.mo.lot_producing_id = self.equipo
        self.mo._mc_sellar_alcance()

        self.assertEqual(alerta.lot_ids, self.equipo)

    def test_no_pisa_un_alcance_puesto_a_mano(self):
        """Quien acotó el daño a mano sabe más que el automatismo."""
        otro = self.env["stock.lot"].create(
            {"name": "SN-CALIDAD-2", "product_id": self.producto.id}
        )
        alerta = self.env["quality.alert"].create(
            {
                "product_tmpl_id": self.plantilla.id,
                "team_id": self.team.id,
                "production_id": self.mo.id,
                "lot_ids": [(6, 0, otro.ids)],
            }
        )

        self.mo.lot_producing_id = self.equipo
        self.mo._mc_sellar_alcance()

        self.assertEqual(alerta.lot_ids, otro)


class TestLeccionesDelModelo(CalidadCommon):
    """Qué ve el que arma el próximo equipo (§ 6.1.1)."""

    def setUp(self):
        super().setUp()
        self.mo = self.env["mrp.production"].create(
            {"product_id": self.producto.id, "product_qty": 1}
        )

    def test_muestra_las_lecciones_del_modelo(self):
        leccion = self._leccion()
        self.assertIn(leccion, self.mo.mc_leccion_ids)
        self.assertEqual(self.mo.mc_leccion_count, 1)

    def test_ignora_las_que_siguen_abiertas(self):
        self._leccion(stage_id=self.etapa_abierta.id)
        self.assertFalse(self.mo.mc_leccion_ids)

    def test_ignora_las_cerradas_sin_accion_preventiva(self):
        """Cerrar arreglando un equipo no es cambiar cómo se arman todos."""
        self._leccion(action_preventive=False)
        self.assertFalse(self.mo.mc_leccion_ids)

    def test_un_html_vacio_no_cuenta_como_accion_preventiva(self):
        """El editor deja "<p><br></p>" cuando alguien entra y no escribe nada.

        En pantalla se ve igual que vacío y en un dominio pasa cualquier `!= False`, así
        que sin esto la pestaña mostraría lecciones que no dicen nada.
        """
        self._leccion(action_preventive="<p><br></p>")
        self.assertFalse(self.mo.mc_leccion_ids)

    def test_ignora_las_de_otro_modelo(self):
        otro = self.env["product.product"].create({"name": "ROV MC-100 Test"})
        self._leccion(product_tmpl_id=otro.product_tmpl_id.id)
        self.assertFalse(self.mo.mc_leccion_ids)

    def test_excluye_las_de_la_propia_orden(self):
        """Lo que se busca es lo aprendido antes; esto ya lo sabe quien mira la pantalla."""
        self._leccion(production_id=self.mo.id)
        self.assertFalse(self.mo.mc_leccion_ids)

    def test_incluye_las_que_vienen_de_reparacion(self):
        """El canal por el que vuelve el patrón que fabricación no podía ver (§ 6.3)."""
        orden = self.env["repair.order"].create({"product_id": self.producto.id})
        leccion = self._leccion(repair_id=orden.id)
        self.assertIn(leccion, self.mo.mc_leccion_ids)

    def test_la_ficha_del_modelo_cuenta_lo_mismo(self):
        self._leccion()
        self._leccion(stage_id=self.etapa_abierta.id)
        self.assertEqual(self.plantilla.mc_leccion_count, 1)


class TestPuenteAlEco(CalidadCommon):
    """«Cambiamos el BoM por esto», que antes no quedaba en ninguna parte (§ 6.1.2)."""

    def test_la_alerta_apunta_al_eco_y_el_eco_devuelve_la_alerta(self):
        tipo = self.env["mrp.eco.type"].search([], limit=1) or self.env["mrp.eco.type"].create(
            {"name": "Maduración (test)"}
        )
        eco = self.env["mrp.eco"].create(
            {
                "name": "ECO test",
                "type_id": tipo.id,
                "type": "product",
                "product_tmpl_id": self.plantilla.id,
            }
        )
        alerta = self._leccion(mc_eco_id=eco.id)

        self.assertEqual(alerta.mc_eco_id, eco)
        self.assertIn(alerta, eco.mc_alerta_ids)
        self.assertEqual(eco.mc_alerta_count, 1)


class TestAlertaDesdeLineaDeTrabajo(CalidadCommon):
    """El botón de la línea de reparación (§ 6.1.3)."""

    def setUp(self):
        super().setUp()
        self.orden = self.env["repair.order"].create(
            {"product_id": self.producto.id, "lot_id": self.equipo.id}
        )
        self.linea = self.env["mc.rov.linea.falla"].create(
            {
                "repair_id": self.orden.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "accion_id": self.env.ref("mc_rov.accion_reparacion").id,
                "origen": "diseno",
                "analisis_causa": "El conector era IP67 y el equipo trabaja sumergido.",
            }
        )

    def test_crea_la_alerta_y_la_deja_enlazada(self):
        self.linea.action_crear_alerta_calidad()

        self.assertTrue(self.linea.mc_alerta_id)
        self.assertEqual(self.linea.mc_alerta_id.repair_id, self.orden)
        self.assertEqual(self.linea.mc_alerta_id.product_tmpl_id, self.plantilla)
        self.assertEqual(self.linea.mc_alerta_id.lot_ids, self.equipo)

    def test_copia_el_razonamiento_a_la_alerta(self):
        """Seis meses después nadie abre la orden de reparación para leerlo."""
        self.linea.action_crear_alerta_calidad()
        descripcion = self.linea.mc_alerta_id.description

        self.assertIn("IP67", descripcion)
        self.assertIn("Diseño o especificación", descripcion)

    def test_el_segundo_clic_abre_la_que_ya_existe(self):
        """Duplicar inflaría el conteo por modelo, que dice si un diseño maduró."""
        self.linea.action_crear_alerta_calidad()
        alerta = self.linea.mc_alerta_id

        accion = self.linea.action_crear_alerta_calidad()

        self.assertEqual(self.linea.mc_alerta_id, alerta)
        self.assertEqual(accion["res_id"], alerta.id)
        self.assertEqual(
            self.env["quality.alert"].search_count([("repair_id", "=", self.orden.id)]), 1
        )

    def test_sin_catalogo_alineado_la_razon_queda_vacia(self):
        """Contrato con el bloque D: la causa raíz se resuelve por XML ID.

        Mientras D no cree `mc_rov.quality_reason_<origen>`, esto queda en blanco y la
        persona la elige a mano. Cuando D exista, el botón empieza a llenarla sin tocar
        una línea de código.
        """
        self.linea.action_crear_alerta_calidad()
        esperado = self.env.ref("mc_rov.quality_reason_diseno", raise_if_not_found=False)
        self.assertEqual(self.linea.mc_alerta_id.reason_id, esperado or self.env["quality.reason"])
