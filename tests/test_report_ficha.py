from pathlib import Path
from runpy import run_path

from lxml import etree, html
from odoo.exceptions import UserError

from .test_mc_rov_revision import RevisionCommon


# El informe cubre escenarios independientes; dividir la clase ocultaría los fixtures comunes.
# pylint: disable=too-many-public-methods
class TestReporteFicha(RevisionCommon):
    """Lo que se entrega al cliente debe respetar la audiencia y no perder líneas."""

    def _imprimir_html(self, revision, opciones=None):
        contenido, _ = (
            self.env["ir.actions.report"]
            .with_context(rov_options=opciones or {})
            ._render_qweb_html(
                "mc_rov.action_report_ficha",
                revision.ids,
            )
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
        self.assertEqual(len(documento.xpath("//*[@data-rov-check]")), len(revision.chequeo_ids))

    def test_cabecera_conserva_banda_y_datos_de_identificacion(self):
        """La cabecera impresa mantiene la jerarquía de la ficha C sin perder datos reales."""
        revision = self._revision()
        documento = self._imprimir_html(revision)

        self.assertTrue(documento.xpath("//*[@data-rov-header-band]"))
        self.assertTrue(documento.xpath('//img[starts-with(@src, "data:image/png;base64,")]'))
        for etiqueta in ("Fecha", "Equipo", "N° de serie", "Propietario", "Técnico"):
            self.assertTrue(
                documento.xpath(f'//*[@data-rov-identity-card and .//*[text()="{etiqueta}"]]'),
                etiqueta,
            )

    def test_tira_reparacion_conserva_cinco_datos(self):
        revision = self._revision(tipo="reparacion")
        documento = self._imprimir_html(revision)
        tarjetas = documento.xpath("//*[@data-rov-identity-card]")

        self.assertEqual(len(tarjetas), 5)
        self.assertFalse(documento.xpath('//*[text()="Tipo de prueba"]'))
        self.assertIn("Ficha de equipo reparado", documento.text_content())

    def test_asistente_rechaza_revision_que_no_es_reparacion(self):
        revision = self._revision(tipo="terreno")
        wizard = self.env["mc.rov.ficha.wizard"].create({"revision_id": revision.id})

        with self.assertRaises(UserError):
            wizard.action_imprimir()

    def test_confirmado_conserva_cero_y_no_aplica(self):
        revision = self._revision(fuga_corriente=0)
        self._corrida_completa(revision)
        self._responder_todo(revision, "no_lo_tiene")
        self._responder_sellos(revision)
        revision.action_confirmar()
        documento = self._imprimir_html(revision)
        self.assertNotIn("BORRADOR", documento.text_content())
        self.assertIn("No aplica", documento.text_content())
        self.assertIn("0", documento.xpath("//*[@data-rov-leakage]")[0].text_content())

    def test_sellos_no_aplica_se_conserva_pero_no_se_imprime(self):
        revision = self._revision()
        sellos = revision.inspeccion_ids
        sellos[0].estado_sello = "intacto"
        sellos[1].estado_sello = "roto"
        sellos[2].estado_sello = "no_lo_tiene"

        documento = self._imprimir_html(revision)
        bloque = documento.xpath("//*[@data-rov-seals]")[0]
        texto = bloque.text_content()

        self.assertEqual(sellos[2].estado_sello, "no_lo_tiene")
        self.assertIn("Intacto", texto)
        self.assertIn("Roto", texto)
        self.assertIn("Pendiente", texto)
        self.assertNotIn("No aplica", texto)
        self.assertEqual(len(bloque.xpath("//*[@data-rov-seal]")), len(sellos) - 1)

    def test_sellos_distinguen_integridad_manipulacion_y_sello_previo(self):
        revision = self._revision()
        estados = ("intacto", "roto", "ausente", "sin_sello_previo")
        for sello, estado in zip(revision.inspeccion_ids, estados):
            sello.estado_sello = estado

        documento = self._imprimir_html(revision)
        bloque = documento.xpath("//*[@data-rov-seals]")[0]
        clases = {
            sello.get("data-rov-seal"): sello.xpath('.//*[contains(@class, "rov-card-value")]')[
                0
            ].get("class", "")
            for sello in bloque.xpath(".//*[@data-rov-seal]")
        }
        estilos = " ".join(documento.xpath("//style/text()"))

        self.assertIn("rov-seal-ok", clases[str(revision.inspeccion_ids[0].id)])
        self.assertIn("rov-seal-fail", clases[str(revision.inspeccion_ids[1].id)])
        self.assertIn("rov-seal-fail", clases[str(revision.inspeccion_ids[2].id)])
        self.assertIn("rov-seal-warning", clases[str(revision.inspeccion_ids[3].id)])
        self.assertIn(".rov-seal-warning { color: #b36b00; }", estilos)

    def test_mediciones_conservan_los_campos_reales_en_paneles(self):
        revision = self._revision(
            funcionamiento_continuo_duracion=1.5,
            funcionamiento_continuo_resultado="ok",
            subida=92.4,
            bajada=88.1,
            presion_bar=30,
            presion_tiempo=2,
            fuga_corriente=0.02,
            consumo_reposo=0.5,
            consumo_carga=1.2,
            luces_internas=4,
            luces_externas=6,
            limitacion_pilot_gain=7555,
            ganancia_luz=4040,
            temperatura_interior=9876.5,
            temperatura_exterior=8765.4,
        )

        documento = self._imprimir_html(revision)
        paneles = documento.xpath("//*[@data-rov-measurement-panel]")
        texto = " ".join(panel.text_content() for panel in paneles)

        self.assertEqual(len(paneles), 6)
        self.assertEqual(
            [panel.get("data-rov-measurement-panel") for panel in paneles],
            ["continuo", "banda", "estanqueidad", "aislacion", "consumo", "luces"],
        )
        self.assertIn("MEDICIONES", documento.text_content())
        self.assertIn("↑", texto)
        self.assertIn("↓", texto)
        banda = documento.xpath('//*[@data-rov-measurement-panel="banda"]')[0]
        etiquetas_banda = " ".join(
            banda.xpath('.//*[contains(@class, "rov-measurement-label")]/text()')
        )
        valores_banda = " ".join(
            banda.xpath('.//*[contains(@class, "rov-measurement-value")]//text()')
        )
        self.assertIn("Subida", etiquetas_banda)
        self.assertIn("Bajada", etiquetas_banda)
        self.assertNotIn("↑", etiquetas_banda)
        self.assertNotIn("↓", etiquetas_banda)
        self.assertIn("↑", valores_banda)
        self.assertIn("↓", valores_banda)
        self.assertEqual(len(banda.xpath('.//*[contains(@class, "rov-measurement-arrow")]')), 2)
        self.assertEqual(
            documento.xpath(
                'string(//*[@data-rov-measurement-panel="continuo"]'
                '//*[contains(@class, "rov-measurement-success")])'
            ).strip(),
            "Sin problemas",
        )
        estilos = " ".join(documento.xpath("//style/text()"))
        self.assertIn("td.rov-measurement-panel", estilos)
        self.assertNotIn("min-height: 54px", estilos)
        for valor in ("1,50", "92,40", "88,10", "30,0", "0,020", "0,50", "1,20", "4", "6"):
            self.assertIn(valor, texto)
        self.assertNotIn("9876", texto)
        self.assertNotIn("8765", texto)
        self.assertNotIn("7555", texto)
        self.assertNotIn("4040", texto)

    def test_chequeos_se_agrupan_sin_ocultar_estados_ni_lineas(self):
        revision = self._revision()
        revision.chequeo_ids[0].resultado = "ok"
        revision.chequeo_ids[1].resultado = "no_ok"
        revision.chequeo_ids[2].resultado = "no_lo_tiene"

        documento = self._imprimir_html(revision)
        bloque = documento.xpath("//*[@data-rov-checks]")[0]
        grupos = bloque.xpath("//*[@data-rov-check-section]")

        self.assertEqual(len(grupos), len(set(revision.chequeo_ids.mapped("seccion"))))
        self.assertEqual(len(bloque.xpath("//*[@data-rov-check]")), len(revision.chequeo_ids))
        texto = bloque.text_content()
        self.assertIn("Conforme", texto)
        self.assertIn("No conforme", texto)
        self.assertIn("No aplica", texto)

    def test_chequeos_muestran_detalle_compacto_y_estados_reales(self):
        revision = self._revision()
        revision.chequeo_ids[0].resultado = "ok"
        revision.chequeo_ids[1].resultado = "no_ok"
        revision.chequeo_ids[2].resultado = "no_lo_tiene"

        documento = self._imprimir_html(revision)
        bloque = documento.xpath("//*[@data-rov-checks]")[0]
        grupos = bloque.xpath(".//*[@data-rov-check-section]")

        self.assertEqual(
            len(bloque.xpath('.//*[contains(@class, "rov-check-separator")]')),
            len(revision.chequeo_ids) - len(grupos),
        )
        self.assertEqual(
            len(bloque.xpath('.//*[@data-rov-check and contains(@class, "rov-check-fail")]')),
            1,
        )
        self.assertEqual(
            len(bloque.xpath('.//*[@data-rov-check and contains(@class, "rov-check-na")]')),
            1,
        )
        self.assertTrue(
            bloque.xpath('.//*[@data-rov-check and contains(@class, "rov-check-pending")]')
        )
        leyenda = bloque.xpath('.//*[contains(@class, "rov-checks-legend")]')[0]
        clases_leyenda = {
            item.text_content().strip(): item.get("class", "") for item in leyenda.xpath("./span")
        }
        self.assertEqual(clases_leyenda["Conforme"], "rov-check-ok")
        self.assertEqual(clases_leyenda["No conforme"], "rov-check-fail")
        self.assertEqual(clases_leyenda["No aplica"], "rov-check-na")
        pendiente = leyenda.xpath('./span[normalize-space()="Pendiente"]')
        self.assertEqual(len(pendiente), 1)
        self.assertEqual(pendiente[0].get("class", ""), "rov-check-pending")
        estilos = " ".join(documento.xpath("//style/text()"))
        self.assertIn(".rov-check-line { display: inline; }", estilos)
        self.assertIn("padding-left: 9.43px;", estilos)
        self.assertIn("overflow-wrap: break-word;", estilos)
        self.assertIn(
            ".rov-ficha .rov-checks-legend { text-align: right; color: #657585; "
            "font-size: 8.66pt; }",
            estilos,
        )
        for clase in (
            "rov-seal-ok",
            "rov-measurement-success",
            "rov-check-summary-ok",
            "rov-check-ok",
        ):
            self.assertRegex(estilos, rf"\.{clase} \{{ color: #007b4b;")
        self.assertIn(
            ".rov-ficha .rov-check-ok { color: #007b4b; }",
            estilos,
        )
        self.assertIn(
            ".rov-ficha .rov-check-fail { color: #b42318; font-weight: 600; }",
            estilos,
        )

    def test_tipografia_y_alturas_minimas_respetan_la_jerarquia_de_la_ficha(self):
        """Evita que tarjetas equivalentes pierdan su reserva de composición."""
        documento = self._imprimir_html(self._revision())
        estilos = " ".join(documento.xpath("//style/text()"))

        self.assertIn(".rov-ficha .rov-section-title {", estilos)
        self.assertIn("letter-spacing: .08em;", estilos)
        self.assertIn("margin: 0 0 7.35px;", estilos)
        self.assertIn(".rov-ficha .rov-report-card { min-height: 164.16px;", estilos)
        self.assertIn(".rov-ficha .rov-closing-card { min-height: 170.56px;", estilos)
        self.assertIn(
            ".rov-ficha .rov-measurement-arrow { font-size: 11.14pt; font-weight: normal;", estilos
        )
        self.assertIn(".rov-ficha .rov-check-details {", estilos)
        self.assertIn("line-height: 1.346;", estilos)

    def test_cierre_deja_zona_de_firma_y_resumen_de_hallazgos(self):
        """La pasada final conserva aire de identificación y firma sin fijar el cierre."""
        documento = self._imprimir_html(self._revision())
        estilos = " ".join(documento.xpath("//style/text()"))

        self.assertIn(
            ".rov-ficha .rov-identity-card { min-height: 50.5px; ",
            estilos,
        )
        self.assertIn(
            ".rov-ficha .rov-finding-summary { margin-top: 8.5px; ",
            estilos,
        )
        self.assertIn(
            ".rov-ficha .rov-signatures { margin-top: 12.66px; ",
            estilos,
        )
        self.assertIn(
            ".rov-ficha .rov-signature-line { height: 47px; ",
            estilos,
        )
        self.assertIn(
            ".rov-ficha .rov-signature-label { font-size: 8.75pt; color: #536779; ",
            estilos,
        )
        self.assertIn(
            ".rov-ficha .rov-footer { font-size: 8.7pt; color: #536779; ",
            estilos,
        )

    def test_navegacion_conserva_todas_las_lineas_con_estados_uniformes(self):
        revision = self._revision()
        navegacion = revision.chequeo_ids.filtered(lambda linea: linea.seccion == "navegacion")

        for estado, clase_resumen, clases_linea in (
            ("ok", "rov-check-summary-ok", {"rov-check-ok"}),
            ("no_ok", "rov-check-summary-fail", {"rov-check-fail"}),
            (
                "mixto",
                "rov-check-summary-fail",
                {
                    "rov-check-ok",
                    "rov-check-fail",
                    "rov-check-na",
                    "rov-check-pending",
                },
            ),
        ):
            if estado == "mixto":
                for indice, linea in enumerate(navegacion):
                    linea.resultado = ("ok", "no_ok", "no_lo_tiene", False)[indice % 4]
            else:
                navegacion.write({"resultado": estado})
            bloque = self._imprimir_html(revision).xpath("//*[@data-rov-checks]")[0]
            seccion = bloque.xpath('//*[@data-rov-check-section="navegacion"]')[0]

            self.assertIn(
                clase_resumen,
                seccion.xpath(".//*[@data-rov-check-summary]")[0].get("class", ""),
            )
            lineas = seccion.xpath(".//*[@data-rov-check]")
            self.assertEqual(len(lineas), len(navegacion))
            self.assertEqual(
                {
                    next(
                        clase
                        for clase in (
                            "rov-check-ok",
                            "rov-check-fail",
                            "rov-check-na",
                            "rov-check-pending",
                        )
                        if clase in linea.get("class", "")
                    )
                    for linea in lineas
                },
                clases_linea,
            )

    def test_chequeos_muestran_etiquetas_de_estado_para_tecnico(self):
        resultado = dict(self.env["mc.rov.revision.chequeo"]._fields["resultado"].selection)

        self.assertEqual(
            resultado,
            {
                "ok": "Conforme",
                "no_ok": "No conforme",
                "no_lo_tiene": "No aplica",
            },
        )

    def test_chequeos_usan_nombre_ficha_y_nombre_completo_como_respaldo(self):
        self.assertIn("nombre_ficha", self.env["mc.rov.chequeo"]._fields)
        corto = self._chequeo_catalogo(
            name="Nombre operativo que no debe imprimirse",
            nombre_ficha="Nombre breve para cliente",
        )
        respaldo = self._chequeo_catalogo(name="Chequeo personalizado sin nombre breve")
        revision = self._revision(tipo="reparacion")
        self.env["mc.rov.revision.chequeo"].create(
            [
                {"revision_id": revision.id, "chequeo_id": corto.id},
                {"revision_id": revision.id, "chequeo_id": respaldo.id},
            ]
        )

        texto = self._imprimir_html(revision).text_content()

        self.assertIn("Nombre breve para cliente", texto)
        self.assertNotIn("Nombre operativo que no debe imprimirse", texto)
        self.assertIn("Chequeo personalizado sin nombre breve", texto)

    def test_resumen_de_grupo_refleja_fallos_pendientes_y_no_aplica(self):
        revision = self._revision()
        por_seccion = {
            seccion: revision.chequeo_ids.filtered(
                lambda linea, actual=seccion: linea.seccion == actual
            )
            for seccion in (
                "energia",
                "inspeccion_fisica",
                "navegacion",
                "accesorios",
                "video",
            )
        }
        por_seccion["energia"].write({"resultado": "ok"})
        por_seccion["inspeccion_fisica"].write({"resultado": "ok"})
        por_seccion["inspeccion_fisica"][0].resultado = "no_ok"
        por_seccion["navegacion"][0].resultado = "ok"
        por_seccion["accesorios"].write({"resultado": "no_lo_tiene"})
        por_seccion["video"][0].resultado = "ok"
        por_seccion["video"][1].resultado = "no_lo_tiene"

        bloque = self._imprimir_html(revision).xpath("//*[@data-rov-checks]")[0]

        for seccion, clase in (
            ("energia", "rov-check-summary-ok"),
            ("inspeccion_fisica", "rov-check-summary-fail"),
            ("navegacion", "rov-check-summary-pending"),
            ("accesorios", "rov-check-summary-na"),
            ("video", "rov-check-summary-na"),
        ):
            resumen = bloque.xpath(
                f'.//*[@data-rov-check-section="{seccion}"]' "//*[@data-rov-check-summary]"
            )[0]
            self.assertIn(clase, resumen.get("class", ""))

        clases_por_seccion = {
            seccion: [
                linea.get("class", "")
                for linea in bloque.xpath(
                    f'.//*[@data-rov-check-section="{seccion}"]//*[@data-rov-check]'
                )
            ]
            for seccion in por_seccion
        }
        self.assertTrue(all("rov-check-ok" in clase for clase in clases_por_seccion["energia"]))
        self.assertIn("rov-check-fail", " ".join(clases_por_seccion["inspeccion_fisica"]))
        self.assertIn("rov-check-pending", " ".join(clases_por_seccion["navegacion"]))
        self.assertTrue(all("rov-check-na" in clase for clase in clases_por_seccion["accesorios"]))
        self.assertIn("rov-check-ok", clases_por_seccion["video"][0])
        self.assertIn("rov-check-na", clases_por_seccion["video"][1])

    def test_pendiente_se_explica_en_leyenda_sin_repetirse_por_linea(self):
        revision = self._revision()
        bloque = self._imprimir_html(revision).xpath("//*[@data-rov-checks]")[0]

        self.assertEqual(bloque.text_content().count("Pendiente"), 1)

    def test_catalogo_estandar_tiene_los_25_nombres_para_ficha(self):
        self.assertIn("nombre_ficha", self.env["mc.rov.chequeo"]._fields)
        esperados = {
            "chequeo_chasis": "Chasis y estructura",
            "chequeo_penetradores": "Penetradores y conectores",
            "chequeo_umbilical_estado": "Umbilical",
            "chequeo_helices_dano": "Hélices",
            "chequeo_enciende": "Encendido y arranque",
            "chequeo_sensor_leak": "Sensor de leak",
            "chequeo_estanqueidad": "Estanqueidad",
            "chequeo_responde_comandos": "Comandos desde superficie",
            "chequeo_ancho_banda": "Ancho de banda",
            "chequeo_software_opera": "Software de superficie",
            "chequeo_software_ficha": "Software según ficha",
            "chequeo_camara": "Imagen de cámara",
            "chequeo_tilt": "Tilt",
            "chequeo_luces_control": "Control de luces",
            "chequeo_helices": "Posición de hélices",
            "chequeo_thrusters": "Thrusters",
            "chequeo_mov_vertical": "Movimiento vertical",
            "chequeo_mov_horizontal": "Movimiento horizontal",
            "chequeo_acro": "Modo acro",
            "chequeo_stabilize": "Stabilize",
            "chequeo_depth_hold": "Depth hold",
            "chequeo_ruido_vibracion": "Ruido y vibración",
            "chequeo_manipulador": "Manipulador",
            "chequeo_salida_brazo": "Salida de brazo",
            "chequeo_sonar": "Sonar",
        }

        self.assertEqual(
            {
                record.get("id"): record.findtext("field[@name='nombre_ficha']")
                for record in etree.parse(
                    str(Path(__file__).resolve().parents[1] / "data/mc_rov_revision_data.xml")
                ).xpath("//record[@model='mc.rov.chequeo']")
            },
            esperados,
        )

    def test_migracion_completa_vacios_y_respeta_personalizaciones(self):
        vacio = self.env.ref("mc_rov.chequeo_enciende")
        personalizado = self.env.ref("mc_rov.chequeo_sensor_leak")
        vacio.write({"name": "Descripción operativa personalizada", "nombre_ficha": False})
        personalizado.nombre_ficha = "Etiqueta propia del taller"
        nuevo = self._chequeo_catalogo(name="Chequeo sin XML ID")
        nombres = (vacio.name, personalizado.name, nuevo.name)
        self.env.flush_all()
        migrate = run_path(
            str(Path(__file__).resolve().parents[1] / "migrations/19.0.23.2.0/post-migrate.py")
        )["migrate"]

        for _ in range(2):
            migrate(self.env.cr, "19.0.23.1.0")
            self.env.invalidate_all()
            self.assertEqual(vacio.nombre_ficha, "Encendido y arranque")
            self.assertEqual(personalizado.nombre_ficha, "Etiqueta propia del taller")
            self.assertFalse(nuevo.nombre_ficha)
            self.assertEqual((vacio.name, personalizado.name, nuevo.name), nombres)

    def test_catalogo_extensible_en_ficha_de_reparacion(self):
        revision = self._revision(tipo="reparacion")
        nuevo = self._chequeo_catalogo(name="Chequeo agregado al catálogo", seccion="otro")
        self.env["mc.rov.revision.chequeo"].create(
            {"revision_id": revision.id, "chequeo_id": nuevo.id, "resultado": "no_ok"}
        )
        documento = self._imprimir_html(revision)

        self.assertIn("Ficha de equipo reparado", documento.text_content())
        self.assertIn("Chequeo agregado al catálogo", documento.text_content())
        filas = documento.xpath(
            '//*[@data-rov-checks]//table[contains(@class, "rov-check-grid")]//tr'
        )
        self.assertTrue(filas)
        self.assertTrue(all(1 <= len(fila.xpath("./td")) <= 3 for fila in filas))

    def test_hallazgos_y_observaciones_se_adaptan_sin_perder_datos(self):
        self.lot.mc_n_serie_umbilical = "4102"
        orden = self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "lot_id": self.lot.id,
                "observaciones_salida": (
                    "Primera línea para el cliente.\n"
                    "Segunda línea extensa que debe envolver naturalmente."
                ),
            }
        )
        revision = self._revision(
            repair_id=orden.id,
            umbilical="equipo",
            umbilical_serie="4471",
        )
        hallazgo = self._hallazgo_privado(
            revision,
            "Hallazgo suficientemente largo para comprobar que el contenido no se recorta",
        )

        documento = self._imprimir_html(revision)
        cierre = documento.xpath("//*[@data-rov-closing-layout]")[0]
        tarjetas = cierre.xpath('./tr/td[contains(@class, "rov-closing-cell")]')
        observaciones = cierre.xpath(".//*[@data-rov-observations]")[0]

        self.assertEqual(len(tarjetas), 2)
        self.assertTrue(
            all("rov-closing-cell-half" in tarjeta.get("class", "") for tarjeta in tarjetas)
        )
        self.assertIn(hallazgo.hallazgo_id.name, cierre.text_content())
        self.assertIn("Primera línea para el cliente.", observaciones.text_content())
        self.assertTrue(observaciones.xpath(".//*[@data-rov-differences]"))
        self.assertIn("4471", observaciones.text_content())
        self.assertIn("4102", observaciones.text_content())

        sin_diferencias = self._imprimir_html(revision, {"diferencias": False})
        self.assertFalse(sin_diferencias.xpath("//*[@data-rov-differences]"))
        self.assertTrue(sin_diferencias.xpath("//*[@data-rov-observations]"))

        solo_hallazgos = self._revision()
        self._hallazgo_privado(solo_hallazgos, "Hallazgo sin observaciones")
        celda_hallazgos = self._imprimir_html(solo_hallazgos).xpath(
            '//*[@data-rov-closing-layout]/tr/td[contains(@class, "rov-closing-cell")]'
        )
        self.assertEqual(len(celda_hallazgos), 1)
        self.assertIn("rov-closing-cell-full", celda_hallazgos[0].get("class", ""))

        orden_solo_observaciones = self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "lot_id": self.lot.id,
                "observaciones_salida": "Observación sin hallazgos",
            }
        )
        solo_observaciones = self._revision(repair_id=orden_solo_observaciones.id)
        celda_observaciones = self._imprimir_html(solo_observaciones).xpath(
            '//*[@data-rov-closing-layout]/tr/td[contains(@class, "rov-closing-cell")]'
        )
        self.assertEqual(len(celda_observaciones), 1)
        self.assertIn("rov-closing-cell-full", celda_observaciones[0].get("class", ""))

        self.assertFalse(
            self._imprimir_html(self._revision()).xpath("//*[@data-rov-closing-layout]")
        )

    def test_hallazgos_cortos_muestran_siete_y_resumen_sin_perder_las_lineas(self):
        revision = self._revision()
        for numero in range(20):
            self._hallazgo_privado(revision, f"Hallazgo visible {numero:02d}")
        documento = self._imprimir_html(revision)
        texto = documento.text_content()

        self.assertEqual(len(revision.hallazgo_ids), 20)
        for numero in range(7):
            self.assertIn(f"Hallazgo visible {numero:02d}", texto)
        self.assertNotIn("Hallazgo visible 07", texto)
        resumen = documento.xpath("//*[@data-rov-findings-summary]")
        self.assertEqual(len(resumen), 1)
        self.assertIn("y 13 hallazgos más", " ".join(resumen[0].text_content().split()))
        self.assertIn("ver en el sistema", resumen[0].text_content())

        revision.hallazgo_ids[8:].unlink()
        resumen_singular = self._imprimir_html(revision).xpath("//*[@data-rov-findings-summary]")
        self.assertEqual(len(resumen_singular), 1)
        self.assertIn("y 1 hallazgo más", " ".join(resumen_singular[0].text_content().split()))

    def test_hallazgos_largos_reducen_visibles_segun_su_peso(self):
        revision = self._revision()
        for numero in range(12):
            self._hallazgo_privado(
                revision,
                f"Aplastamiento localizado junto al conector principal {numero:02d}",
            )

        documento = self._imprimir_html(revision)
        texto = documento.text_content()

        for numero in range(5):
            self.assertIn(f"conector principal {numero:02d}", texto)
        self.assertNotIn("conector principal 05", texto)
        resumen = documento.xpath("//*[@data-rov-findings-summary]")
        self.assertEqual(len(resumen), 1)
        self.assertIn("y 7 hallazgos más", " ".join(resumen[0].text_content().split()))

    def test_firmas_pie_y_borrador_siguen_la_composicion_de_la_ficha(self):
        documento = self._imprimir_html(self._revision())

        marca = documento.xpath("//*[@data-rov-watermark]")
        self.assertEqual(len(marca), 1)
        self.assertEqual(marca[0].text_content().strip(), "BORRADOR")

        firmas = documento.xpath("//*[@data-rov-signatures]")[0]
        self.assertEqual(len(firmas.xpath('.//*[contains(@class, "rov-signature-line")]')), 2)
        self.assertIn("Firma del técnico", firmas.text_content())
        self.assertIn("Jefe de taller", firmas.text_content())
        self.assertNotIn("___", firmas.text_content())

        pie = documento.xpath("//*[@data-rov-footer]")[0]
        texto_pie = " ".join(pie.text_content().split())
        for valor in (
            "Ingeniería y Servicios Marine Connection SpA",
            "RUT 76.957.685-1",
            "Pje. Chinquihue 136, Puerto Montt",
            "+56 9 7646 3823",
            "marineconnection.cl",
        ):
            self.assertIn(valor, texto_pie)

    def test_opciones_no_cambian_la_revision(self):
        revision = self._revision()
        documento = self._imprimir_html(revision, {"firmas": False, "sellos": False})
        self.assertFalse(documento.xpath("//*[@data-rov-signatures]"))
        self.assertFalse(documento.xpath("//*[@data-rov-seals]"))
        self.assertEqual(revision.estado, "borrador")

    def test_asistente_selecciona_documento_y_opciones(self):
        revision = self._revision()
        wizard = self.env["mc.rov.ficha.wizard"].create(
            {"revision_id": revision.id, "mostrar_firmas": False}
        )
        accion = wizard.action_imprimir()
        self.assertEqual(accion["report_name"], "mc_rov.report_ficha")
        self.assertFalse(accion["context"]["rov_options"]["firmas"])

    def test_orden_ofrece_selector_sin_escoger_una_de_varias_revisiones(self):
        orden = self.env["repair.order"].create(
            {"product_id": self.product.id, "lot_id": self.lot.id}
        )
        self.assertTrue(hasattr(orden, "action_imprimir_ficha"))
        with self.assertRaises(UserError):
            orden.action_imprimir_ficha()

        primera = self._revision(repair_id=orden.id)
        accion = orden.action_imprimir_ficha()
        self.assertEqual(accion["res_model"], "mc.rov.ficha.wizard")
        self.assertEqual(accion["context"]["default_repair_id"], orden.id)
        self.assertEqual(accion["context"]["default_revision_id"], primera.id)

        self._revision(repair_id=orden.id)
        accion = orden.action_imprimir_ficha()
        self.assertFalse(accion["context"].get("default_revision_id"))

        vista = etree.fromstring(
            self.env.ref("mc_rov.view_repair_order_form_mc_rov").arch_db.encode()
        )
        self.assertTrue(
            vista.xpath(
                "//button[@name='action_nueva_revision']"
                "/following-sibling::button[@name='action_imprimir_ficha']"
            )
        )

    def test_selector_de_orden_no_imprime_una_revision_de_otra_visita(self):
        self.assertIn("repair_id", self.env["mc.rov.ficha.wizard"]._fields)
        orden = self.env["repair.order"].create(
            {"product_id": self.product.id, "lot_id": self.lot.id}
        )
        otra_orden = self.env["repair.order"].create(
            {"product_id": self.product.id, "lot_id": self.lot.id}
        )
        ajena = self._revision(repair_id=otra_orden.id)
        wizard = self.env["mc.rov.ficha.wizard"].create(
            {"repair_id": orden.id, "revision_id": ajena.id}
        )

        with self.assertRaises(UserError):
            wizard.action_imprimir()
