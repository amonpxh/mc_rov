from lxml import html

from .test_mc_rov_revision import RevisionCommon


class TestReporteFicha(RevisionCommon):
    """Lo que se entrega al cliente debe respetar la audiencia y no perder líneas."""

    def _imprimir_html(self, revision, opciones=None):
        contenido, _ = self.env["ir.actions.report"].with_context(
            rov_options=opciones or {}
        )._render_qweb_html(
            "mc_rov.action_report_ficha",
            revision.ids,
        )
        return html.fromstring(contenido)

    def _hallazgo_privado(self, revision, nombre="Hallazgo de prueba"):
        componente = self.env["mc.rov.componente"].create({"name": "Componente de prueba"})
        catalogo = self.env["mc.rov.hallazgo"].create({"name": nombre})
        return self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
                "componente_id": componente.id,
                "hallazgo_id": catalogo.id,
                "detalle": "DETALLE_INTERNO_NO_ENTREGAR",
                "severidad": "impide_operar",
            }
        )

    def test_borrador_no_inventa_respuestas_ni_filtra_internos(self):
        revision = self._revision(temperatura_interior=9876.5)
        self._hallazgo_privado(revision)
        documento = self._imprimir_html(revision)
        texto = documento.text_content()
        self.assertIn("BORRADOR", texto)
        self.assertIn("Pendiente", texto)
        self.assertNotIn("9876", texto)
        self.assertNotIn("Veredicto", texto)
        self.assertNotIn("Severidad", texto)
        self.assertNotIn("DETALLE_INTERNO_NO_ENTREGAR", texto)
        self.assertNotIn("Impide operar", texto)
        self.assertIn("Hallazgo de prueba", texto)
        self.assertEqual(
            len(documento.xpath('//*[@data-rov-check]')), len(revision.chequeo_ids)
        )

    def test_confirmado_conserva_cero_y_no_aplica(self):
        revision = self._revision(fuga_corriente=0)
        self._corrida_completa(revision)
        self._responder_todo(revision, "no_lo_tiene")
        self._responder_sellos(revision)
        revision.action_confirmar()
        documento = self._imprimir_html(revision)
        self.assertNotIn("BORRADOR", documento.text_content())
        self.assertIn("No aplica", documento.text_content())
        self.assertIn("0", documento.xpath('//*[@data-rov-leakage]')[0].text_content())

    def test_catalogo_extensible_y_tipos_de_aceptacion(self):
        for tipo in ("rendimiento", "terreno"):
            revision = self._revision(tipo=tipo)
            self._hallazgo_privado(revision, "HALLAZGO_NUEVO_NO_ENTREGAR")
            nuevo = self._chequeo_catalogo(name="Chequeo agregado al catálogo", seccion="otro")
            self.env["mc.rov.revision.chequeo"].create(
                {"revision_id": revision.id, "chequeo_id": nuevo.id, "resultado": "no_ok"}
            )
            documento = self._imprimir_html(revision)
            self.assertIn("Ficha de equipo nuevo", documento.text_content())
            self.assertIn("Chequeo agregado al catálogo", documento.text_content())
            self.assertFalse(documento.xpath('//*[@data-rov-findings]'))
            self.assertFalse(documento.xpath('//*[@data-rov-seals]'))
            self.assertNotIn("HALLAZGO_NUEVO_NO_ENTREGAR", documento.text_content())
            if tipo == "terreno":
                self.assertFalse(documento.xpath('//*[@data-rov-leakage]'))

    def test_hallazgos_no_se_truncan_para_entrar_en_una_hoja(self):
        revision = self._revision()
        for numero in range(20):
            self._hallazgo_privado(revision, f"Hallazgo visible {numero:02d}")
        texto = self._imprimir_html(revision).text_content()
        for numero in range(20):
            self.assertIn(f"Hallazgo visible {numero:02d}", texto)

    def test_opciones_no_cambian_la_revision(self):
        revision = self._revision()
        documento = self._imprimir_html(revision, {"firmas": False, "sellos": False})
        self.assertFalse(documento.xpath('//*[@data-rov-signatures]'))
        self.assertFalse(documento.xpath('//*[@data-rov-seals]'))
        self.assertEqual(revision.estado, "borrador")

    def test_asistente_selecciona_documento_y_opciones(self):
        revision = self._revision()
        wizard = self.env["mc.rov.ficha.wizard"].create(
            {"revision_id": revision.id, "mostrar_firmas": False}
        )
        accion = wizard.action_imprimir()
        self.assertEqual(accion["report_name"], "mc_rov.report_ficha")
        self.assertFalse(accion["context"]["rov_options"]["firmas"])
