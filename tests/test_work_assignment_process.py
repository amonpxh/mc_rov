from odoo.exceptions import ValidationError

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
