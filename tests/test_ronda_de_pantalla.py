"""Lo que sale de recorrer las pantallas, ronda por ronda.

Los defectos que encuentra Paulo mirando el sistema en uso no caen en un modelo ni en un
concepto: caen en el borde entre lo que el código hace y lo que la pantalla deja creer. Van
juntos acá porque lo que tienen en común es cómo se encontraron.
"""

from odoo.tests import tagged

from .test_mc_rov_revision import RevisionCommon


@tagged("post_install", "-at_install")
class TestRondaDePantalla8(RevisionCommon):
    """Lo que salió de recorrer la revisión en staging el 2026-08-24."""

    def _confirmable(self, **vals):
        revision = self._revision(**vals)
        self._corrida_completa(revision)
        self._responder_todo(revision)
        self._responder_sellos(revision)
        return revision

    def test_un_borrador_no_tiene_veredicto(self):
        """Y esto se decide en el cálculo, no en la vista.

        `19.0.18.3.0` lo escondió del formulario y dejó el cálculo intacto, así que la columna
        «Resultado» de las listas seguía anunciando «Aprobado» sobre un borrador. Se cubre
        leyendo el campo y no la pantalla, que es donde estaba el hueco.
        """
        revision = self._confirmable()

        self.assertFalse(revision.resultado)

        revision.action_confirmar()
        self.assertEqual(revision.resultado, "aprobado")

    def test_volver_a_borrador_retira_el_veredicto(self):
        revision = self._confirmable()
        revision.action_confirmar()

        revision.action_volver_a_borrador()

        self.assertFalse(revision.resultado)

    def test_la_foto_de_la_ficha_sigue_a_la_ficha_mientras_es_borrador(self):
        """El orden natural de trabajo es abrir la prueba y llenar la ficha después.

        Hasta 19.0.20.0.0 la foto se tomaba solo al crear, así que en ese orden la revisión
        comparaba contra campos vacíos — y un campo vacío no afirma nada, de modo que no
        avisaba nada. Lo encontró Paulo haciendo exactamente eso.
        """
        revision = self._revision()
        self.assertFalse(revision.luces_ficha)

        self.lot.mc_cantidad_luces = 6
        revision.horas_operacion = 10  # cualquier guardado

        self.assertEqual(revision.luces_ficha, 6)

    def test_confirmada_la_foto_deja_de_seguir_a_la_ficha(self):
        """El otro lado de lo mismo: un documento emitido no cambia solo."""
        self.lot.mc_cantidad_luces = 6
        revision = self._confirmable()
        revision.action_confirmar()

        self.lot.mc_cantidad_luces = 2
        revision.horas_operacion = 10

        self.assertEqual(revision.luces_ficha, 6)

    def test_otro_controlador_de_vuelo_marca_diferencia(self):
        """La comparación miraba las tres versiones y no las piezas.

        Cambiar el controlador es un hallazgo más grande que cambiarle la versión, y hasta
        19.0.20.0.0 pasaba sin decir nada.
        """
        Controlador = self.env["mc.rov.controlador.vuelo"]
        self.lot.mc_controlador_vuelo = Controlador.create({"name": "Navigator"}).id
        revision = self._revision(tipo="reparacion")

        revision.controlador_instalado_id = Controlador.create({"name": "Pixhawk"}).id

        self.assertTrue(revision.software_difiere)

    def test_el_aviso_dice_cual_campo_no_cuadra(self):
        """«El software no coincide» sin decir en qué obliga a compararlos a ojo."""
        revision = self._revision(tipo="reparacion")
        self.lot.mc_version_ardusub = "4.1.0"
        revision.version_ardusub_instalada = "4.0.2"

        self.assertTrue(revision.software_difiere)
        self.assertIn("ArduSub", revision.software_diferencias)

    def test_un_campo_vacio_sigue_sin_afirmar_nada(self):
        """La regla de siempre, ahora sobre cinco campos en vez de tres."""
        self.lot.mc_version_ardusub = "4.1.0"
        revision = self._revision(tipo="reparacion")

        self.assertFalse(revision.software_difiere)
        self.assertFalse(revision.software_diferencias)
