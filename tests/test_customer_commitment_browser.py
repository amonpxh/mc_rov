"""QA de F3 sobre documentos nativos y una transferencia ficticia validada."""

from datetime import timedelta

from odoo import Command, fields
from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user

from ..models.production_kpi_metrics import local_day


def prepare_f3_case(env, warehouse, label, *, outgoing=True):
    """Genera una visita propia y, si corresponde, su salida física de prueba."""
    # pylint: disable=too-many-locals
    company = warehouse.company_id
    category = env["product.category"].create({"name": f"QA F3 {label}"})
    env["ir.config_parameter"].set_param("mc_rov.rov_category_id", str(category.id))
    product = env["product.product"].create(
        {
            "name": f"ROV QA F3 {label}",
            "tracking": "serial",
            "is_storable": True,
            "categ_id": category.id,
            "company_id": company.id,
        }
    )
    lot = env["stock.lot"].create({"name": f"F3-{label}", "product_id": product.id})
    customer = env["res.partner"].create({"name": f"Cliente QA F3 {label}"})
    repair = env["repair.order"].create(
        {
            "company_id": company.id,
            "product_id": product.id,
            "product_uom": product.uom_id.id,
            "lot_id": lot.id,
            "partner_id": customer.id,
        }
    )
    if not outgoing:
        return repair, env["stock.picking"], env["ir.attachment"]
    stock = warehouse.lot_stock_id
    destination = customer.property_stock_customer
    env["stock.quant"]._update_available_quantity(product, stock, 1, lot_id=lot)
    picking = env["stock.picking"].create(
        {
            "company_id": company.id,
            "picking_type_id": warehouse.out_type_id.id,
            "location_id": stock.id,
            "location_dest_id": destination.id,
            "partner_id": customer.id,
            "move_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "product_uom": product.uom_id.id,
                        "product_uom_qty": 1,
                        "location_id": stock.id,
                        "location_dest_id": destination.id,
                    }
                )
            ],
        }
    )
    picking.action_confirm()
    picking.action_assign()
    assert picking.move_line_ids.lot_id == lot, "No se reservó la serie ficticia"
    picking.move_ids.picked = True
    picking.button_validate()
    assert picking.state == "done", "No se validó la salida de prueba"
    attachment = env["ir.attachment"].create(
        {
            "name": "Acta de retiro QA F3",
            "type": "url",
            "url": "https://example.com/constancia-qa-f3",
            "res_model": "stock.picking",
            "res_id": picking.id,
        }
    )
    return repair, picking, attachment


def promise_wizard(repair, now, **changes):
    """Usa la entrada normal de Reparación y fija tiempos compartidos por los actores."""
    action = repair.action_mc_customer_commitment()
    return (
        repair.env[action["res_model"]]
        .with_context(**action["context"])
        .create(
            {
                "promised_date": local_day(now),
                "agreed_at": now - timedelta(days=2),
                "evidence": "Acuerdo original QA F3",
                **changes,
            }
        )
    )


def dispatch_wizard(picking, repair, attachment, now):
    """Prepara una constancia usando el asistente abierto para esa transferencia."""
    action = picking.action_open_customer_dispatch()
    wizard = picking.env[action["res_model"]].browse(action["res_id"])
    wizard.write(
        {
            "mode": "pickup",
            "effective_date": local_day(now),
            "attachment_id": attachment.id,
            "repair_ids": [Command.set(repair.ids)],
        }
    )
    return wizard


@tagged("post_install", "-at_install", "kpi_dashboard_browser", "customer_commitment_browser")
class TestCustomerCommitmentBrowser(HttpCase):
    """Recorre historial, constancia y tablero con Supervisor y Taller."""

    browser_size = "1440x1000"

    def _visit(self, path, login, checks):
        self.browser_js(
            path,
            """
            (async () => {
                const until = async (predicate) => {
                    for (let n = 0; n < 300; n++) {
                        const result = predicate();
                        if (result) return result;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw new Error('No apareció el resultado esperado de F3');
                };
                const visible = selector => [...document.querySelectorAll(selector)]
                    .find(element => element.getClientRects().length);
                CHECKS
                console.log('test successful');
            })().catch(error => console.error(error));
            """.replace(
                "CHECKS", checks
            ),
            login=login,
            timeout=85,
        )

    def test_operational_repair_pickup_and_dashboard(self):
        # pylint: disable=too-many-locals
        company = self.env["res.company"].create({"name": "QA Operativa F3"})
        env = self.env(context={**self.env.context, "allowed_company_ids": company.ids})
        warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
        repair, picking, attachment = prepare_f3_case(env, warehouse, "OPERATIVA")
        groups = "base.group_user,mc_rov.group_work_assignment_team"
        supervisor = new_test_user(
            env,
            login="qa_f3_operational_supervisor",
            company_id=company.id,
            groups=groups
            + ",stock.group_stock_manager,mc_rov.group_customer_commitment_supervisor",
        )
        workshop = new_test_user(
            env,
            login="qa_f3_operational_workshop",
            company_id=company.id,
            groups=groups + ",stock.group_stock_user",
        )
        now = fields.Datetime.now()
        visit = repair.with_user(supervisor)
        promise_wizard(visit, now).action_apply()
        promise_wizard(
            visit,
            now,
            operation="reprogram",
            promised_date=local_day(now) + timedelta(days=1),
            agreed_at=now - timedelta(days=1),
            reason="Ventana acordada QA F3",
        ).action_apply()
        service = env["mc.rov.customer.commitment.kpi"].with_user(supervisor)
        self.assertEqual(service.get_summary()["due"]["unknown"], 1)
        dispatch_wizard(picking.with_user(supervisor), visit, attachment, now).action_apply()
        self.assertEqual(service.get_summary()["completed"]["on_time"], 1)
        self._visit(
            f"/odoo/repair.order/{repair.id}",
            workshop.login,
            """
            const history = await until(() => visible('button[name="action_mc_customer_commitments"]'));
            if (visible('button[name="action_mc_customer_commitment"]')) throw Error('Taller puede registrar');
            history.click();
            await until(() => document.querySelector('.modal')?.textContent.includes('Ventana acordada QA F3'));
            if (!document.querySelector('.modal').textContent.includes('Acuerdo original QA F3')) {
                throw Error('Falta la promesa original en historial');
            }
            """,
        )
        self._visit(
            f"/odoo/stock.picking/{picking.id}",
            supervisor.login,
            """
            const tab = await until(() => [...document.querySelectorAll('.o_notebook .nav-link')]
                .find(node => node.textContent.trim() === 'Constancia de salida'));
            tab.click();
            const button = await until(() => visible('button[name="action_open_customer_dispatch"]'));
            await until(() => document.querySelector('.o_form_view')?.textContent.includes('Acta de retiro QA F3'));
            button.click();
            await until(() => visible('.modal button[name="action_apply"]'));
            """,
        )
        action = env.ref("mc_rov.action_kpi_dashboard")
        self.browser_size = "390x844"
        self._visit(
            f"/odoo/action-{action.id}",
            supervisor.login,
            """
            const section = await until(() => visible('[data-section="commitments"]'));
            section.click();
            const board = await until(() => visible('[data-kpi-commitments]'));
            await until(() => [...board.querySelectorAll('.mc_kpi_value')]
                .filter(value => value.textContent.trim() === '1 de 1').length === 2);
            if (board.scrollWidth > board.clientWidth + 1) throw Error('F3 desborda en móvil');
            """,
        )
