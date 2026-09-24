from lxml import html

from odoo.exceptions import UserError, ValidationError

from .test_mc_rov_revision import RevisionCommon


class TestFichaEquipoNuevo(RevisionCommon):
    """La ficha consolida dos pruebas elegidas sin alterar su trazabilidad."""

    def _ficha(self, rnd=None, trn=None, **vals):
        return self.env["mc.rov.ficha.equipo.nuevo"].create(
            {
                "lot_id": self.lot.id,
                "rnd_id": rnd.id if rnd else False,
                "trn_id": trn.id if trn else False,
                **vals,
            }
        )

    def _aprobada(self, tipo, **vals):
        revision = self._revision(tipo=tipo, **vals)
        self._responder_todo(revision)
        if tipo == "rendimiento":
            self._corrida_completa(revision)
        self._emitir(revision)
        self.assertEqual(revision.resultado, "aprobado")
        return revision

    def test_equipo_propone_pruebas_recientes_pero_las_deja_elegir(self):
        rnd_anterior = self._aprobada("rendimiento", fecha="2026-09-21")
        rnd_nueva = self._aprobada("rendimiento", fecha="2026-09-23")
        trn = self._aprobada("terreno", fecha="2026-09-22")
        self._revision(tipo="terreno", fecha="2026-09-24", estado="borrador")
        accion = self.lot.action_preparar_ficha_equipo_nuevo()
        self.assertEqual(accion["res_model"], "mc.rov.ficha.equipo.nuevo.wizard")
        self.assertEqual(accion["context"]["default_rnd_id"], rnd_nueva.id)
        self.assertEqual(accion["context"]["default_trn_id"], trn.id)
        wizard = self.env["mc.rov.ficha.equipo.nuevo.wizard"].create(
            {"lot_id": self.lot.id, "rnd_id": rnd_anterior.id, "trn_id": trn.id}
        )
        self.assertEqual(wizard.rnd_id, rnd_anterior)

    def test_no_mezcla_pruebas_de_otro_equipo_ni_tipos(self):
        rnd = self._revision(tipo="rendimiento")
        otro_lote = self.env["stock.lot"].create(
            {"name": "ROV-OTRO", "product_id": self.product.id}
        )
        trn_otro = self.env["mc.rov.revision"].create({"lot_id": otro_lote.id, "tipo": "terreno"})
        with self.assertRaises(ValidationError):
            self._ficha(rnd, trn_otro)
        with self.assertRaises(ValidationError):
            self._ficha(rnd, rnd)

    def test_borrador_no_se_emite_si_falta_una_prueba_aprobada(self):
        rnd = self._revision(tipo="rendimiento")
        trn = self._revision(tipo="terreno")
        ficha = self._ficha(rnd, trn)
        with self.assertRaises(UserError):
            ficha.action_emitir()
        self.assertEqual(ficha.estado, "borrador")
        self.assertFalse(ficha.pdf_attachment_id)

    def test_resumen_refleja_checklist_real_y_fallo_rechaza_emision(self):
        rnd = self._aprobada("rendimiento")
        trn = self._revision(tipo="terreno")
        accesorio = trn.chequeo_ids.filtered(lambda linea: linea.seccion == "accesorios")[:1]
        self.assertTrue(accesorio)
        self._responder_todo(trn)
        accesorio.resultado = "no_ok"
        self._emitir(trn)
        self.assertEqual(trn.resultado, "rechazado")
        grupo = next(
            grupo
            for grupo in self._ficha(rnd, trn)._ficha_grupos_chequeos(trn)
            if grupo["nombre"] == "accesorios"
        )
        self.assertEqual(
            grupo["total"], len(trn.chequeo_ids.filtered(lambda l: l.seccion == "accesorios"))
        )
        self.assertEqual(grupo["estilo"], "fail")
        self.assertIn(
            accesorio.chequeo_id.nombre_ficha or accesorio.chequeo_id.name,
            [linea["nombre"] for linea in grupo["lineas"]],
        )
        with self.assertRaises(UserError):
            self._ficha(rnd, trn).action_emitir()

    def test_emision_guarda_pdf_y_no_cambia_con_ediciones_del_equipo(self):
        rnd = self._aprobada("rendimiento")
        trn = self._aprobada("terreno")
        ficha = self._ficha(rnd, trn)
        ficha.action_emitir()
        self.assertEqual(ficha.estado, "emitida")
        self.assertTrue(ficha.pdf_attachment_id)
        firma = ficha.pdf_attachment_id.checksum
        self.lot.mc_chasis = "Inox"
        self.assertEqual(ficha.pdf_attachment_id.checksum, firma)
        with self.assertRaises(UserError):
            ficha.write({"rnd_id": False})

    def test_qweb_usa_datos_reales_y_oculta_temperaturas(self):
        self.lot.write(
            {
                "mc_chasis": "Inox",
                "mc_n_motores": 6,
                "mc_modelo_motores": "T200",
                "mc_n_serie_umbilical": "UMB-TEST-26",
                "mc_cantidad_luces": 6,
            }
        )
        rnd = self._revision(tipo="rendimiento", subida=23.0, temperatura_interior=9876.5)
        trn = self._revision(tipo="terreno", lugar="Bahía de prueba", profundidad=120)
        ficha = self._ficha(rnd, trn)
        contenido, _ = self.env["ir.actions.report"]._render_qweb_html(
            "mc_rov.action_report_ficha_equipo_nuevo", ficha.ids
        )
        documento = html.fromstring(contenido)
        texto = documento.text_content()
        for valor in (ficha.name, self.lot.name, rnd.name, trn.name, "UMB-TEST-26", "120"):
            self.assertIn(valor, texto)
        self.assertNotIn("9876", texto)
        self.assertNotIn("Modelo de fuente", texto)
        self.assertEqual(len(documento.xpath("//*[@data-fen-validation]")), 2)
