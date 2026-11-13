"""Pruebas reales de navegador, separadas de la suite sin HTTP del módulo."""

from unittest.mock import patch

from odoo import Command, fields
from odoo.tests import HttpCase, tagged
from odoo.tests.common import ChromeBrowser, new_test_user

from .test_mc_rov_revision import RevisionCommon


@tagged("post_install", "-at_install", "kpi_dashboard_browser")
class TestKPIDashboardBrowser(HttpCase):
    """Comprueba HOOT y la pantalla nativa sin consultar empresas operativas."""

    browser_size = "1440x1000"

    def _volume_fixture(self, company, category):
        """Genera hechos por acciones reales; nunca escribe el ledger privado."""
        # Una preparación cohesiva permite verificar el recorrido completo por unidad.
        # pylint: disable=too-many-locals
        env = self.env(context={**self.env.context, "allowed_company_ids": company.ids})
        warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
        if not warehouse:
            warehouse = env["stock.warehouse"].create(
                {"name": "QA Taller indicadores", "code": "KPV", "company_id": company.id}
            )
        product = env["product.product"].create(
            {
                "name": "ROV QA visual",
                "tracking": "serial",
                "is_storable": True,
                "categ_id": category.id,
                "company_id": company.id,
            }
        )
        customer = env["res.partner"].create({"name": "Cliente QA visual"})
        repaired_lot, new_lot = env["stock.lot"].create(
            [
                {"name": name, "product_id": product.id, "company_id": company.id}
                for name in ("QA-VIS-REPARACION", "QA-VIS-FABRICACION")
            ]
        )
        repair = env["repair.order"].create(
            {
                "product_id": product.id,
                "product_qty": 1,
                "lot_id": repaired_lot.id,
                "company_id": company.id,
                "partner_id": customer.id,
                "tipo_intervencion_ids": [
                    Command.set(env.ref("mc_rov.tipo_reparacion_correctiva").ids)
                ],
            }
        )
        repair.action_repair_done()
        bom = env["mrp.bom"].create(
            {"product_tmpl_id": product.product_tmpl_id.id, "company_id": company.id}
        )
        production = env["mrp.production"].create(
            {
                "product_id": product.id,
                "product_qty": 1,
                "product_uom_id": product.uom_id.id,
                "bom_id": bom.id,
                "company_id": company.id,
                "picking_type_id": warehouse.manu_type_id.id,
            }
        )
        production.action_confirm()
        production.write({"lot_producing_ids": [Command.set(new_lot.ids)], "qty_producing": 1})
        production.with_context(skip_redirection=True).button_mark_done()
        employee = env["hr.employee"].create(
            {"name": "Técnico QA visual", "company_id": company.id}
        )
        revisions = env["mc.rov.revision"].create(
            [
                {"lot_id": new_lot.id, "tipo": kind, "responsable_id": employee.id}
                for kind in ("rendimiento", "terreno")
            ]
        )
        for revision in revisions:
            RevisionCommon._corrida_completa(self, revision)
            RevisionCommon._responder_todo(self, revision)
            RevisionCommon._responder_sellos(self, revision)
            revision.write({"mc_correction_required": "no", "mc_retest_required": "no"})
        for name, component in (("Corrosión QA", "Motor QA"), ("Conexión QA", "Conector QA")):
            finding = env["mc.rov.hallazgo"].create({"name": name})
            part = env["mc.rov.componente"].create({"name": component})
            env["mc.rov.revision.hallazgo"].create(
                {
                    "revision_id": revisions[0].id,
                    "hallazgo_id": finding.id,
                    "componente_id": part.id,
                    "severidad": "informativo",
                    "mc_detected_at": fields.Datetime.now(),
                }
            )
        env["mc.rov.new.acceptance"].start_attempt(
            production.id, new_lot.id, revisions[0].id, revisions[1].id
        )
        revisions.action_confirmar()
        fen = env["mc.rov.ficha.equipo.nuevo"].create(
            {"lot_id": new_lot.id, "rnd_id": revisions[0].id, "trn_id": revisions[1].id}
        )
        fen.action_emitir()
        production._release_rov_unit(new_lot, fen, True)

    def _volume_layout(self, size, section):
        company = self.env["res.company"].create({"name": "QA Producción y hallazgos"})
        category = self.env["product.category"].create({"name": "QA ROV visual poblado"})
        self.env["ir.config_parameter"].set_param("mc_rov.rov_category_id", str(category.id))
        self._volume_fixture(company, category)
        viewer = new_test_user(
            self.env,
            login="qa_volume_visual",
            groups="base.group_user,stock.group_stock_user,mrp.group_mrp_user,mc_rov.group_work_assignment_team",
            company_id=company.id,
            lang="es_CL",
        )
        report = self.env["mc.rov.production.kpi"].with_user(viewer).get_summary(revision="all")
        self.assertEqual(report["repair"]["visits"], 1)
        self.assertEqual(report["manufacturing"]["released"], 1)
        self.assertEqual(report["findings"]["total"], 2)
        self.browser_size = size
        original = ChromeBrowser._wait_code_ok  # pylint: disable=protected-access

        def capture(browser, *args, **kwargs):
            try:
                return original(browser, *args, **kwargs)
            finally:
                result = browser._websocket_request(
                    "Page.captureScreenshot", params={"format": "png"}
                )  # pylint: disable=protected-access
                self._logger.info(
                    "CI_VOLUME_SCREENSHOT size=%s section=%s data=%s",
                    size,
                    section,
                    result["data"],
                )

        action = self.env.ref("mc_rov.action_kpi_dashboard")
        with patch.object(ChromeBrowser, "_wait_code_ok", capture):
            self.browser_js(
                f"/odoo/action-{action.id}",
                """
                (async () => {
                    const wait = async (predicate) => { for (let n = 0; n < 600; n++) {
                        if (predicate()) return; await new Promise(r => setTimeout(r, 100));
                    } throw new Error('No apareció la sección poblada'); };
                    await wait(() => document.querySelector('[data-section="production"]'));
                    const root = document.querySelector('.mc_kpi_dashboard');
                    root.querySelector('[data-section="production"]').click();
                    await wait(() => root.querySelector('[data-volume="manufactured"]'));
                    const revision = root.querySelector('[data-kpi-revision]');
                    revision.value = 'all'; revision.dispatchEvent(new Event('change', {bubbles:true}));
                    await wait(() => root.querySelector('[data-volume="repair"] .mc_kpi_value')?.textContent === '1');
                    if (root.scrollWidth > root.clientWidth + 1) throw new Error('Producción desborda');
                    root.querySelector('[data-section="findings"]').click();
                    await wait(() => root.querySelectorAll('.mc_kpi_pareto_row').length === 2);
                    if (root.scrollWidth > root.clientWidth + 1) throw new Error('Hallazgos desborda');
                    if (!root.textContent.includes('Corrosión QA')) throw new Error('Falta Pareto real');
                    if (FINAL_SECTION === 'production') {
                        root.querySelector('[data-section="production"]').click();
                        await wait(() => root.querySelector(
                            '[data-volume="released"] .mc_kpi_value')?.textContent === '1');
                    } else {
                        root.querySelector('.mc_kpi_pareto').scrollIntoView({block: 'start'});
                    }
                    console.log('test successful');
                })().catch(error => console.error(error));
            """.replace(
                    "FINAL_SECTION", repr(section)
                ),
                login=viewer.login,
                timeout=180,
            )

    def _layout(self, size):
        company = self.env["res.company"].create({"name": "QA Tablero visual"})
        category = self.env["product.category"].create({"name": "QA Vehículos tablero"})
        self.env["ir.config_parameter"].set_param("mc_rov.rov_category_id", str(category.id))
        viewer = new_test_user(
            self.env,
            login="qa_dashboard_visual",
            groups="base.group_user,stock.group_stock_user,mrp.group_mrp_user,mc_rov.group_work_assignment_team",
            company_id=company.id,
            lang="es_CL",
        )
        self.browser_size = size
        # Separar un error del servicio de un fallo de montaje o estilo del navegador.
        report = self.env["mc.rov.kpi.dashboard"].with_user(viewer).get_dashboard()
        self.assertEqual(report["cohort"]["company_ids"], company.ids)
        action = self.env.ref("mc_rov.action_kpi_dashboard")
        original_wait = ChromeBrowser._wait_code_ok  # pylint: disable=protected-access

        def capture(browser, *args, **kwargs):
            try:
                return original_wait(browser, *args, **kwargs)
            finally:
                # Solo cuenta/empresa ficticias; el log preservado permite inspección visual.
                result = browser._websocket_request(  # pylint: disable=protected-access
                    "Page.captureScreenshot", params={"format": "png"}
                )
                self._logger.info("CI_KPI_SCREENSHOT size=%s data=%s", size, result["data"])

        with patch.object(ChromeBrowser, "_wait_code_ok", capture):
            self._open_layout(action, viewer)

    def _open_layout(self, action, viewer):
        self.browser_js(
            f"/odoo/action-{action.id}",
            """
            (async () => {
                const wait = async (predicate) => {
                    for (let n = 0; n < 600; n++) {
                        if (predicate()) return;
                        await new Promise((resolve) => setTimeout(resolve, 100));
                    }
                    throw new Error("No apareció el tablero o la sección esperada");
                };
                await wait(() => document.querySelectorAll(".mc_kpi_quality").length === 2);
                const root = document.querySelector(".mc_kpi_dashboard");
                if (!root.textContent.includes("QA Tablero visual")) throw new Error("Empresa QA incorrecta");
                if (root.querySelector("[role='alert']")) throw new Error("Error RPC del tablero");
                if (root.scrollWidth > root.clientWidth + 1) throw new Error("Desborde horizontal");
                const cards = [...root.querySelectorAll(".mc_kpi_quality")];
                const [first, second] = cards.map((card) => card.getBoundingClientRect());
                const sameRow = Math.abs(first.top - second.top) < 2;
                if (sameRow !== (innerWidth >= 768)) throw new Error("Columnas incorrectas para el ancho");
                root.querySelector("[data-section='coverage']").click();
                await wait(() => root.querySelectorAll("[data-family]").length === 11);
                if (!root.textContent.includes("Fórmula:")) throw new Error("Faltan definiciones");
                root.querySelector("[data-section='tracking']").click();
                await wait(() => root.querySelector("[data-kpi-process]"));
                if (root.scrollWidth > root.clientWidth + 1) throw new Error("Seguimiento desborda la pantalla");
                root.querySelector("[data-section='summary']").click();
                await wait(() => root.querySelectorAll(".mc_kpi_quality").length === 2);
                console.log("test successful");
            })().catch((error) => console.error(error));
            """,
            login=viewer.login,
            timeout=180,
        )

    def test_desktop_layout(self):
        self._layout("1440x1000")

    def test_mobile_layout(self):
        self._layout("390x844")

    def test_production_populated_desktop(self):
        self._volume_layout("1440x1000", "production")

    def test_findings_populated_mobile(self):
        self._volume_layout("390x844", "findings")

    def test_hoot_dashboard_and_existing_controls(self):
        company = self.env["res.company"].create({"name": "QA HOOT tablero"})
        viewer = new_test_user(
            self.env,
            login="qa_dashboard_hoot",
            groups="base.group_user,base.group_system",
            company_id=company.id,
        )
        # Hash nativo HOOT del módulo completo @mc_rov; incluye los once casos nuevos.
        self.browser_js(
            "/web/tests?headless&loglevel=2&preset=desktop&timeout=15000&id=f92f0bf0",
            "",
            login=viewer.login,
            timeout=420,
            success_signal="[HOOT] Test suite succeeded",
            error_checker=lambda message: "[HOOT]" not in message,
        )
