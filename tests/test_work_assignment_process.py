from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .inventory_activity_common import InventoryActivityCommon
from .test_work_assignment import ActivityAssignmentCommon


class TestWorkAssignmentProcess(ActivityAssignmentCommon):
    """Cruza el trabajo con su origen real, sin inferir procesos por nombres."""

    def _service(self):
        service = self.env["mc.rov.work.assignment"].with_user(self.taller)
        self.assertTrue(
            callable(getattr(type(service), "get_processes", None)),
            "Missing assigned work process filter",
        )
        return service

    def _ids(self, action):
        return self.env[action["res_model"]].with_user(self.taller).search(action["domain"]).ids

    def test_reparacion_cruza_usuario_y_empleado(self):
        service = self._service()
        pedro = self._activity(self.pedro)
        self._activity(self.ana)
        action = service.action_activities(process="repair", employee_id=self.pedro.id)
        self.assertEqual(self._ids(action), pedro.ids)

    def test_accion_abierta_incluye_nuevas_actividades_que_cumplen_filtros(self):
        first = self._activity(self.pedro)
        action = self._service().action_activities(process="repair", employee_id=self.pedro.id)
        second = self._activity(self.pedro)
        excluded = self._activity(self.ana)
        ids = self._ids(action)
        self.assertIn(first.id, ids)
        self.assertIn(second.id, ids)
        self.assertNotIn(excluded.id, ids)

    def test_filtro_distingue_documento_de_diseno_y_reparacion(self):
        service = self._service()
        repair = self._activity(self.pedro)
        design = self._activity(self.pedro)
        design.write(
            {
                "res_model_id": self.env["ir.model"]._get_id("product.product"),
                "res_id": self.product.id,
            }
        )
        self.assertEqual(self._ids(service.action_activities(process="repair")), repair.ids)
        self.assertEqual(self._ids(service.action_activities(process="design")), design.ids)

    def test_aceptacion_no_infiere_actividades_de_equipo(self):
        service = self._service()
        self.product.tracking = "serial"
        lot = self.env["stock.lot"].create(
            {
                "name": "QA serie filtro de proceso",
                "product_id": self.product.id,
                "company_id": self.company.id,
            }
        )
        activity = self._activity(self.pedro)
        activity.write(
            {"res_model_id": self.env["ir.model"]._get_id("stock.lot"), "res_id": lot.id}
        )
        self.assertEqual(self._ids(service.action_activities(process="equipment")), activity.ids)
        self.assertFalse(self._ids(service.action_activities(process="acceptance")))
        options = {item["key"]: item for item in service.get_processes(kind="activities")}
        self.assertTrue(options["acceptance"]["available"])
        self.assertFalse(options["acceptance"]["hint"])

    def test_tarea_sin_vinculo_no_hereda_proceso_por_titulo(self):
        service = self._service()
        task = self.env["project.task"].create(
            {
                "name": "Reparar equipo QA: titulo no acredita origen",
                "user_ids": [(4, self.taller.id)],
                "company_id": self.company.id,
            }
        )
        # Consultar tareas requiere Proyecto; el permiso solo afecta a este fixture.
        self.taller.group_ids = [(4, self.env.ref("project.group_project_user").id)]
        self.assertFalse(self._ids(service.action_tasks(process="repair")))
        self.assertIn(task.id, self._ids(service.action_tasks(process="none")))

    def test_proceso_desconocido_y_origen_restringido(self):
        service = self._service()
        activity = self._activity(self.pedro)
        with self.assertRaises(ValidationError):
            service.action_activities(process="inventado")
        self.env["ir.rule"].create(
            {
                "name": "QA origen restringido filtro de proceso",
                "model_id": self.env["ir.model"]._get_id("repair.order"),
                "domain_force": repr([("id", "!=", self.order.id)]),
            }
        )
        self.assertNotIn(activity.id, self._ids(service.action_activities(process="repair")))


class InventoryProcessCommon(InventoryActivityCommon):
    """Actividades propias de stock, independientes de la activación de automatismos."""

    def _stock_activity(self, picking=None, user=None, employee=None, own_type=False):
        picking = picking if picking is not None else self._picking()
        return self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("stock.picking"),
                "res_id": picking.id,
                "activity_type_id": self.env.ref(
                    "mc_rov.activity_type_inventory_receipt"
                    if own_type
                    else "mail.mail_activity_data_todo"
                ).id,
                "summary": "QA actividad logística",
                "user_id": (user or self.operator).id,
                "mc_employee_id": employee.id if employee else False,
            }
        )

    def _stock_service(self, user=None):
        return (
            self.env["mc.rov.work.assignment"]
            .with_user(user or self.operator)
            .with_context(allowed_company_ids=self.env.company.ids)
        )

    def _visible(self, action, user=None):
        return (
            self.env[action["res_model"]]
            .with_user(user or self.operator)
            .with_context(**action["context"])
            .search(action["domain"])
        )


@tagged("post_install", "-at_install")
class TestInventoryProcessNativeFixtures(InventoryProcessCommon):
    """Las actividades nativas y la protección de documentos deben funcionar durante RED."""

    def test_stock_user_reads_activity_on_own_picking(self):
        activity = self._stock_activity()
        action = self._stock_service().action_activities()
        self.assertIn(activity, self._visible(action))
        self.assertEqual(activity.res_model, "stock.picking")

    def test_account_without_stock_does_not_read_source_activity(self):
        activity = self._stock_activity(user=self.outsider)
        self.assertFalse(
            self.env["mail.activity"].with_user(self.outsider).search([("id", "=", activity.id)])
        )


@tagged("post_install", "-at_install")
class TestInventoryWorkAssignmentProcess(InventoryProcessCommon):
    """Inventario clasifica el origen inmediato y conserva los filtros del trabajo asignado."""

    def _service(self, user=None):
        service = self._stock_service(user)
        options = {item["key"]: item for item in service.get_processes(kind="activities")}
        self.assertIn("inventory", options, "Missing inventory assigned process")
        return service

    def test_inventory_option_available_for_stock_account(self):
        options = {item["key"]: item for item in self._service().get_processes()}
        self.assertEqual(options["inventory"]["label"], "Inventario")
        self.assertTrue(options["inventory"]["available"])
        self.assertFalse(options["inventory"]["hint"])

    def test_inventory_option_unavailable_without_stock_access(self):
        options = {item["key"]: item for item in self._service(self.outsider).get_processes()}
        self.assertFalse(options["inventory"]["available"])
        self.assertTrue(options["inventory"]["hint"])

    def test_inventory_uses_picking_source_instead_of_activity_title(self):
        service = self._service()
        inventory = self._stock_activity()
        inventory.summary = "QA diagnóstico de equipo: título ajeno"
        other = self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("product.product"),
                "res_id": self.product.id,
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "summary": "Gestionar recepción",
                "user_id": self.operator.id,
            }
        )
        visible = self._visible(service.action_activities(process="inventory"))
        self.assertIn(inventory, visible)
        self.assertNotIn(other, visible)

    def test_none_process_excludes_picking_activities(self):
        activity = self._stock_activity()
        self.assertNotIn(
            activity, self._visible(self._stock_service().action_activities(process="none"))
        )

    def test_inventory_keeps_employee_filter(self):
        service = self._service()
        first, second = self.env["hr.employee"].create(
            [
                {"name": "QA Logística uno", "company_id": self.env.company.id},
                {"name": "QA Logística dos", "company_id": self.env.company.id},
            ]
        )
        included = self._stock_activity(employee=first)
        excluded = self._stock_activity(employee=second)
        visible = self._visible(
            service.action_activities(process="inventory", employee_id=first.id)
        )
        self.assertIn(included, visible)
        self.assertNotIn(excluded, visible)

    def test_inventory_keeps_mine_and_team_scopes(self):
        self._service()
        self.coordinator.group_ids = [
            Command.link(self.env.ref("mc_rov.group_work_assignment_team").id)
        ]
        mine = self._stock_activity()
        team = self._stock_activity(user=self.coordinator)
        visible = self._visible(self._service().action_activities(process="inventory"))
        self.assertIn(mine, visible)
        self.assertNotIn(team, visible)
        action = self._service(self.coordinator).action_activities(
            scope="team", process="inventory"
        )
        both = self._visible(action, self.coordinator)
        self.assertIn(mine, both)
        self.assertIn(team, both)

    def test_inventory_rechecks_restricted_source(self):
        service = self._service()
        activity = self._stock_activity()
        self.env["ir.rule"].create(
            {
                "name": "QA Inventario origen restringido del filtro",
                "model_id": self.env["ir.model"]._get_id("stock.picking"),
                "domain_force": repr([("id", "!=", activity.res_id)]),
            }
        )
        self.assertNotIn(activity, self._visible(service.action_activities(process="inventory")))

    def test_inventory_keeps_active_company_context(self):
        self._service()
        own = self._stock_activity()
        other = self._other_company()
        kind = self._other_type(other)
        self.operator.company_ids = [Command.link(other.id)]
        picking = (
            self.env["stock.picking"]
            .with_company(other)
            .create(
                {
                    "picking_type_id": kind.id,
                    "location_id": kind.default_location_src_id.id,
                    "location_dest_id": kind.default_location_dest_id.id,
                }
            )
        )
        foreign = self._stock_activity(picking=picking)
        action = self._service().action_activities(process="inventory")
        self.assertIn(own, self._visible(action))
        self.assertNotIn(foreign, self._visible(action))
        action = (
            self._service()
            .with_context(allowed_company_ids=other.ids)
            .action_activities(process="inventory")
        )
        self.assertIn(foreign, self._visible(action))
        self.assertNotIn(own, self._visible(action))

    def test_inventory_action_domain_includes_new_matching_work(self):
        service = self._service()
        first = self._stock_activity()
        action = service.action_activities(process="inventory")
        second = self._stock_activity()
        self.assertIn(first, self._visible(action))
        self.assertIn(second, self._visible(action))

    def test_inventory_does_not_add_project_links(self):
        service = self._service()
        for kind in ("tasks", "projects"):
            options = {item["key"]: item for item in service.get_processes(kind=kind)}
            self.assertFalse(options["inventory"]["available"])
            self.assertEqual(service._process_domain("inventory", kind), [("id", "=", False)])

    def test_inventory_includes_own_and_manual_activity_types(self):
        service = self._service()
        manual = self._stock_activity()
        own = self._stock_activity(own_type=True)
        visible = self._visible(service.action_activities(process="inventory"))
        self.assertIn(manual, visible)
        self.assertIn(own, visible)
