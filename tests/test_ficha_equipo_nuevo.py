from pathlib import Path
import re

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

    def test_fen_no_sustituye_rnd_ausente_por_una_revision_de_reparacion(self):
        reparacion = self._revision(tipo="reparacion")
        trn = self._revision(tipo="terreno")
        ficha = self._ficha(trn=trn)

        contenido, _ = self.env["ir.actions.report"]._render_qweb_html(
            "mc_rov.action_report_ficha_equipo_nuevo", ficha.ids
        )
        documento = html.fromstring(contenido)
        validaciones = documento.xpath("//*[@data-fen-validation]")

        self.assertEqual(len(validaciones), 2)
        self.assertIn("RND pendiente", validaciones[0].text_content())
        self.assertIn(trn.name, validaciones[1].text_content())
        self.assertNotIn(reparacion.name, " ".join(v.text_content() for v in validaciones))

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

    def test_pares_de_chequeos_conservan_orden_y_no_descartan_seccion(self):
        rnd = self._aprobada("rendimiento")
        ficha = self._ficha(rnd, self._revision(tipo="terreno"))

        grupos = ficha._ficha_grupos_chequeos(rnd)
        pares = ficha._ficha_pares_chequeos(rnd)

        self.assertEqual(
            [grupo for par in pares for grupo in par if grupo],
            grupos,
        )
        self.assertEqual(
            [grupo["nombre"] for grupo in pares[0]],
            ["energía", "presión"],
        )
        self.assertEqual(
            [grupo["nombre"] for grupo in pares[-1]],
            ["accesorios", "luces"],
        )
        grupos_impares = [{"nombre": nombre} for nombre in ("A", "B", "C")]
        self.assertEqual(
            ficha._ficha_emparejar_grupos(grupos_impares),
            [(grupos_impares[0], grupos_impares[1]), (grupos_impares[2], False)],
        )
        contenido, _ = self.env["ir.actions.report"]._render_qweb_html(
            "mc_rov.action_report_ficha_equipo_nuevo", ficha.ids
        )
        documento = html.fromstring(contenido)
        filas = documento.xpath("//table[contains(@class, 'fen-check-grid-table')]/tbody/tr")
        self.assertEqual(len(filas), 8)
        self.assertTrue(all(len(fila.xpath("./td")) == 2 for fila in filas))

    def test_emision_guarda_pdf_y_no_cambia_con_ediciones_del_equipo(self):
        rnd = self._aprobada("rendimiento")
        trn = self._aprobada("terreno")
        ficha = self._ficha(rnd, trn)
        ficha.action_emitir()
        self.assertEqual(ficha.estado, "emitida")
        self.assertTrue(ficha.pdf_attachment_id)
        firma = ficha.pdf_attachment_id.checksum
        pdf_emitido = ficha.pdf_attachment_id.raw
        self.lot.mc_chasis = "Inox"
        self.assertEqual(ficha.pdf_attachment_id.checksum, firma)
        self.assertEqual(ficha.pdf_attachment_id.raw, pdf_emitido)
        self.assertEqual(
            ficha.action_descargar()["url"],
            f"/web/content/{ficha.pdf_attachment_id.id}?download=true",
        )
        with self.assertRaises(UserError):
            ficha.write({"rnd_id": False})

    def test_chequeos_extensos_resumen_sin_ocultar_excepciones(self):
        rnd = self._aprobada("rendimiento")
        trn = self._aprobada("terreno")
        ficha = self._ficha(rnd, trn)
        self.assertEqual(ficha._ficha_modo_chequeos(), "normal")
        for index, linea in enumerate(rnd.chequeo_ids[:6]):
            linea.chequeo_id.nombre_ficha = (
                "Verificación extendida de configuración, respuesta y compatibilidad "
                f"de accesorios en secuencia de aceptación {index + 1}"
            )
        excepcion = trn.chequeo_ids.filtered(lambda linea: linea.seccion == "accesorios")[:1]
        excepcion.resultado = "no_ok"
        self.assertEqual(ficha._ficha_modo_chequeos(), "summary")
        contenido, _ = self.env["ir.actions.report"]._render_qweb_html(
            "mc_rov.action_report_ficha_equipo_nuevo", ficha.ids
        )
        documento = html.fromstring(contenido)
        self.assertEqual(len(documento.xpath("//*[contains(@class, 'fen-checks-summary')]")), 2)
        self.assertIn(
            excepcion.chequeo_id.nombre_ficha or excepcion.chequeo_id.name,
            documento.text_content(),
        )
        self.assertIn("No conforme", documento.text_content())

    def test_firmas_van_fuera_de_observaciones_y_despues_de_la_nota(self):
        rnd = self._aprobada("rendimiento")
        trn = self._aprobada("terreno")
        self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": trn.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
                "severidad": "informativo",
            }
        )
        ficha = self._ficha(rnd, trn, observacion="Aceptación técnica registrada.")
        contenido, _ = self.env["ir.actions.report"]._render_qweb_html(
            "mc_rov.action_report_ficha_equipo_nuevo", ficha.ids
        )
        documento = html.fromstring(contenido)
        observaciones = documento.xpath("//*[contains(@class, 'fen-observations')]")[0]
        firmas = documento.xpath("//table[contains(@class, 'fen-signatures')]")[0]
        texto = observaciones.xpath(".//*[contains(@class, 'fen-observation-text')]")[0]
        nota = observaciones.xpath(".//*[contains(@class, 'fen-amber-note')]")[0]
        footer = documento.xpath("//*[contains(@class, 'fen-footer')]")[0]

        self.assertEqual(len(firmas.xpath("./tr/td")), 4)
        self.assertEqual(firmas.getparent(), observaciones.getparent())
        self.assertEqual(footer.getparent(), observaciones.getparent())
        self.assertLess(list(observaciones).index(texto), list(observaciones).index(nota))
        self.assertLess(
            list(observaciones.getparent()).index(observaciones),
            list(observaciones.getparent()).index(firmas),
        )
        self.assertLess(
            list(observaciones.getparent()).index(firmas),
            list(observaciones.getparent()).index(footer),
        )

    def test_observaciones_vacias_muestran_placeholder_solo_sin_nota_ambar(self):
        rnd = self._aprobada("rendimiento")
        trn = self._aprobada("terreno")
        ficha_vacia = self._ficha(rnd, trn)
        contenido, _ = self.env["ir.actions.report"]._render_qweb_html(
            "mc_rov.action_report_ficha_equipo_nuevo", ficha_vacia.ids
        )
        documento = html.fromstring(contenido)
        tarjeta = documento.xpath("//*[contains(@class, 'fen-observations')]")[0]
        placeholder = tarjeta.xpath(".//*[@data-fen-empty-observations]")
        self.assertEqual(len(placeholder), 1)
        self.assertEqual(
            " ".join(placeholder[0].text_content().split()),
            "Sin observaciones registradas en sistema.",
        )
        estilos = " ".join(documento.xpath("//style/text()"))
        self.assertRegex(estilos, r"\.fen-empty-placeholder\s*\{[^}]*font-style:\s*italic")
        self.assertRegex(estilos, r"\.fen-empty-placeholder\s*\{[^}]*font-weight:\s*normal")
        self.assertRegex(
            estilos, r"\.fen-empty-placeholder\s*\{[^}]*font-size:\s*[6-9](?:\.\d+)?pt"
        )

        ficha_con_texto = self._ficha(rnd, trn, observacion="Aceptación ya registrada.")
        contenido, _ = self.env["ir.actions.report"]._render_qweb_html(
            "mc_rov.action_report_ficha_equipo_nuevo", ficha_con_texto.ids
        )
        tarjeta_con_texto = html.fromstring(contenido).xpath(
            "//*[contains(@class, 'fen-observations')]"
        )[0]
        self.assertIn("Aceptación ya registrada.", tarjeta_con_texto.text_content())
        self.assertFalse(tarjeta_con_texto.xpath(".//*[@data-fen-empty-observations]"))

    def test_nota_ambar_sin_observacion_no_muestra_placeholder(self):
        rnd = self._aprobada("rendimiento")
        trn = self._revision(tipo="terreno")
        self._responder_todo(trn)
        self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": trn.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
                "severidad": "informativo",
            }
        )
        self._emitir(trn)
        self.assertEqual(trn.resultado, "aprobado_con_observaciones")
        ficha = self._ficha(rnd, trn)
        contenido, _ = self.env["ir.actions.report"]._render_qweb_html(
            "mc_rov.action_report_ficha_equipo_nuevo", ficha.ids
        )
        tarjeta = html.fromstring(contenido).xpath("//*[contains(@class, 'fen-observations')]")[0]
        self.assertTrue(tarjeta.xpath(".//*[contains(@class, 'fen-amber-note')]"))
        self.assertFalse(tarjeta.xpath(".//*[@data-fen-empty-observations]"))

    def test_qweb_usa_datos_reales_y_oculta_temperaturas(self):
        # Valida en conjunto el contrato de contenido y recursos del PDF FEN.
        # pylint: disable=too-many-locals
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
        estilos = "\n".join(documento.xpath("//style/text()"))
        for valor in (ficha.name, self.lot.name, rnd.name, trn.name, "UMB-TEST-26", "120"):
            self.assertIn(valor, texto)
        self.assertNotIn("9876", texto)
        self.assertNotIn("Modelo de fuente", texto)
        self.assertFalse(documento.xpath("//*[contains(@class, 'fen-watermark')]"))
        self.assertEqual(len(documento.xpath("//*[@data-fen-validation]")), 2)
        self.assertIn("font-family:'Noto Sans'", estilos)
        self.assertIn(".mc-report-identity {", estilos)
        self.assertIn(".fen-check-detail { color:#526b80;", estilos)
        self.assertIn(".fen-footer {", estilos)
        self.assertIn("color:#526b80; font-size:9.2pt;", estilos)
        fuente = Path(__file__).resolve().parents[1] / "static/src/fonts/NotoSans-SemiBold.ttf"
        self.assertTrue(fuente.is_file())
        self.assertTrue(
            (Path(__file__).resolve().parents[1] / "scripts/install_report_font.sh").is_file()
        )

    def test_paleta_impresa_fen_usa_tokens_compartidos(self):
        # La cascada se comprueba para cada rol de borde de la composición.
        # pylint: disable=too-many-locals
        rnd = self._aprobada("rendimiento")
        trn = self._aprobada("terreno")
        documento = html.fromstring(
            self.env["ir.actions.report"]._render_qweb_html(
                "mc_rov.action_report_ficha_equipo_nuevo", self._ficha(rnd, trn).ids
            )[0]
        )
        estilos = " ".join(documento.xpath("//style/text()"))

        def ultima_regla(selector):
            reglas = []
            selector_objetivo = ", ".join(parte.strip() for parte in selector.split(","))
            for selectores, declaraciones in re.findall(r"([^{}]+)\{([^{}]*)\}", estilos):
                selector_regla = ", ".join(parte.strip() for parte in selectores.split(","))
                if selector_regla == selector_objetivo:
                    reglas.append(declaraciones)
            self.assertTrue(reglas, f"Falta la regla CSS {selector}")
            return reglas[-1]

        borde = re.search(
            r"border:\s*1px solid (#[0-9a-fA-F]{6})",
            ultima_regla(".mc-report-head .mc-report-identity td.mc-report-identity-cell"),
        )
        self.assertIsNotNone(borde)
        color_borde = borde.group(1).lower()
        self.assertEqual(color_borde, "#9fb4c3")
        for selector in (".fen-card", ".fen-config-col", ".fen-val-frame"):
            self.assertRegex(ultima_regla(selector), rf"border:\s*1px solid {color_borde}")
        checks = ultima_regla(".fen-check-item")
        self.assertIn("border:0", checks)
        self.assertIn("border-radius:2pt", checks)
        self.assertIn("background:#fff", checks)
        self.assertRegex(checks, r"padding:2pt 3\.15pt")
        self.assertRegex(
            ultima_regla(".fen-check-grid-table"),
            r"border-spacing:4pt 2\.75pt",
        )

        identidad = ultima_regla(".mc-report-head .mc-report-identity td.mc-report-identity-cell")
        self.assertIn("background:#e7eef3", identidad)
        self.assertIn("color:#526b80", ultima_regla(".mc-report-label"))
        for selector in (
            ".fen-key",
            ".fen-revision-meta",
            ".fen-vr-group-title",
            ".fen-vr-line > span",
            ".fen-check-detail",
            ".fen-empty-placeholder",
            ".fen-sign-label",
            ".fen-footer",
        ):
            self.assertIn("color:#526b80", ultima_regla(selector))
        self.assertIn("color:#526b80", ultima_regla(".fen-check-line.ok"))
        self.assertIn("color:#b42318", ultima_regla(".fen-check-score.fail, .fen-check-line.fail"))
        # Cada RND/TRN es una tarjeta interna con gutter blanco y esquinas recortadas.
        shell = ultima_regla(".fen-val-shell")
        frame = ultima_regla(".fen-val-frame")
        self.assertIn("margin:2.5pt", shell)
        self.assertIn("border-radius:4pt", frame)
        self.assertIn("overflow:hidden", frame)
        self.assertIn("background:#edf3f8", frame)
        self.assertIn("border:0", ultima_regla(".fen-val-table"))
        self.assertRegex(ultima_regla(".fen-val-table"), r"height:176pt; min-height:176pt;")
        self.assertEqual(len(documento.xpath("//*[@data-fen-validation]")), 2)
        self.assertEqual(len(documento.xpath('//*[contains(@class, "fen-val-shell")]')), 2)
        self.assertEqual(len(documento.xpath('//*[contains(@class, "fen-val-frame")]')), 2)
        tablas_validacion = documento.xpath('//*[contains(@class, "fen-val-table")]')
        self.assertEqual(len(tablas_validacion), 2)
        # Validar las tres columnas por sus clases semánticas. El selector
        # `.//tr[1]` puede devolver varias filas en XPath (una por cada padre)
        # y hacer frágil el conteo posicional de celdas.
        for tabla in tablas_validacion:
            for columna in ("fen-val-head", "fen-val-mid", "fen-val-side"):
                self.assertEqual(
                    len(
                        tabla.xpath(
                            f'.//*[contains(concat(" ", normalize-space(@class), " "), " {columna} ")]'
                        )
                    ),
                    1,
                    f"La tarjeta de validación debe conservar una columna {columna}",
                )
        self.assertIn("border-top:.58pt solid #8fa6b7", ultima_regla(".fen-sign-line"))
        self.assertIn("border-top:1px solid #8fa6b7", ultima_regla(".fen-footer"))
        self.assertIn("#007b4b", ultima_regla(".fen-check-score.ok"))
        self.assertIn("#667a89", ultima_regla(".fen-check-score.pending, .fen-check-line.pending"))

    def test_cabecera_y_metadata_usan_componente_compartido_a5(self):
        rnd = self._aprobada("rendimiento")
        trn = self._aprobada("terreno")
        ficha = self._ficha(rnd, trn)

        contenido, _ = self.env["ir.actions.report"]._render_qweb_html(
            "mc_rov.action_report_ficha_equipo_nuevo", ficha.ids
        )
        documento = html.fromstring(contenido)
        cabecera = documento.xpath("//*[@data-mc-report-header]")
        metadata = documento.xpath("//*[@data-mc-report-identity]")
        componente = documento.xpath('//*[@data-mc-report-component="header-metadata"]')
        self.assertEqual(len(cabecera), 1)
        self.assertEqual(len(metadata), 1)
        self.assertEqual(len(componente), 1)
        self.assertIn("Ficha de equipo nuevo", cabecera[0].text_content())
        self.assertIn(ficha.name, cabecera[0].text_content())
        self.assertEqual(len(metadata[0].xpath(".//*[@data-mc-report-id]")), 5)

        estilos = "\n".join(documento.xpath("//style/text()"))
        self.assertIn(".mc-report-header {", estilos)
        self.assertIn("height:79pt; min-height:79pt;", estilos)
        self.assertIn("top:4.8pt; left:0;", estilos)
        self.assertIn("top:38pt; left:0;", estilos)
        self.assertIn("top:27.5pt; right:12pt;", estilos)
        self.assertIn("margin:7.2pt -5pt 6.5pt;", estilos)
        self.assertIn("width:133pt;", estilos)
        self.assertIn("font-size:22pt;", estilos)
        self.assertIn("width:16.34%;", estilos)
        self.assertIn("width:22.37%;", estilos)
        self.assertIn("width:18.48%;", estilos)
        self.assertIn("width:22.96%;", estilos)
        self.assertIn("width:19.85%;", estilos)
        self.assertIn("height:40pt;", estilos)
        self.assertIn(".mc-report-head .mc-report-identity td.mc-report-identity-cell {", estilos)
        self.assertIn("padding:6.45pt 6.8pt 3.8pt;", estilos)
        self.assertNotIn("fen-header", estilos)

    def test_metadata_larga_se_compacta_solo_en_values_y_wrappea(self):
        cliente = "CLIENTE DE PRUEBA EXTENDIDO SPA Y SERVICIOS SUBMARINOS"
        responsable = "RESPONSABLE DE INTEGRACION Y PRUEBAS DE ACEPTACION"
        ficha = self._ficha(
            cliente_nombre=cliente,
            responsable_id=self.empleado.id,
        )
        ficha.responsable_id.name = responsable

        contenido, _ = self.env["ir.actions.report"]._render_qweb_html(
            "mc_rov.action_report_ficha_equipo_nuevo", ficha.ids
        )
        documento = html.fromstring(contenido)
        valores = documento.xpath(
            '//*[@data-mc-report-identity]//span[contains(concat(" ", normalize-space(@class), " "), '
            '" mc-report-value ")]'
        )
        compactos = documento.xpath(
            '//*[@data-mc-report-identity]//span[contains(concat(" ", normalize-space(@class), " "), '
            '" mc-report-value--compact ")]'
        )
        etiquetas = documento.xpath(
            '//*[@data-mc-report-identity]//span[@class="mc-report-label"]'
        )
        estilos = "\n".join(documento.xpath("//style/text()"))

        self.assertIn(cliente, documento.text_content())
        self.assertIn(responsable, documento.text_content())
        self.assertEqual(len(valores), 5)
        self.assertEqual(
            {valor.text_content() for valor in compactos}, {cliente, responsable.upper()}
        )
        self.assertTrue(all("compact" not in etiqueta.get("class", "") for etiqueta in etiquetas))
        normales = [
            valor for valor in valores if "mc-report-value--compact" not in valor.get("class", "")
        ]
        self.assertEqual(len(normales), 3)
        self.assertIn("font-size:7.8pt;", estilos)
        self.assertIn("font-size:9.7pt;", estilos)
        self.assertIn("font-size:8pt; line-height:1;", estilos)
        self.assertIn("white-space:normal; overflow-wrap:break-word;", estilos)
        self.assertIn("word-wrap:break-word;", estilos)
        self.assertFalse(documento.xpath('//*[contains(@class, "fen-id-long")]'))
