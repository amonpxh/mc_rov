"""Pruebas reales de navegador, separadas de la suite sin HTTP del módulo."""

from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user


@tagged("post_install", "-at_install", "kpi_dashboard_browser")
class TestKPIDashboardBrowser(HttpCase):
    """Comprueba HOOT y la pantalla nativa sin consultar empresas operativas."""

    browser_size = "1440x1000"

    def _layout(self, size):
        company = self.env["res.company"].create({"name": "QA Tablero visual"})
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
