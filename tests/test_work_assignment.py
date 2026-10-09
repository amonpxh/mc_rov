from unittest.mock import patch

from lxml import etree

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user


class ActivityAssignmentCommon(TransactionCase):
    """Registros reales y transaccionales para probar cuentas compartidas."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.taller = new_test_user(
            cls.env,
            login="qa_assignment_taller",
            groups="stock.group_stock_user",
            company_id=cls.company.id,
        )
        cls.pedro, cls.ana = cls.env["hr.employee"].create(
            [
                {"name": "QA ejecutor Pedro", "company_id": cls.company.id},
                {"name": "QA ejecutora Ana", "company_id": cls.company.id},
            ]
        )
        cls.product = cls.env["product.product"].create({"name": "QA componente taller"})
        cls.order = cls.env["repair.order"].create(
            {
                "product_id": cls.product.id,
                "company_id": cls.company.id,
                "user_id": cls.taller.id,
            }
        )
        cls.activity_type = cls.env.ref("mail.mail_activity_data_todo")

    def _activity(self, employee=False):
        self.assertIn(
            "mc_employee_id",
            self.env["mail.activity"]._fields,
            "Falta la asignación de empleado en actividades nativas",
        )
        return self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("repair.order"),
                "res_id": self.order.id,
                "activity_type_id": self.activity_type.id,
                "summary": "QA acción de taller",
                "user_id": self.taller.id,
                "mc_employee_id": employee.id if employee else False,
                "date_deadline": "2026-10-20",
            }
        )


class TestActivityEmployeeAssignment(ActivityAssignmentCommon):
    """La cuenta compartida y la persona ejecutora conservan identidades distintas."""

    def test_cuenta_compartida_distingue_dos_empleados(self):
        first = self._activity(self.pedro)
        second = self._activity(self.ana)
        self.assertEqual(first.user_id, second.user_id)
        self.assertEqual(first.mc_employee_id, self.pedro)
        self.assertEqual(second.mc_employee_id, self.ana)
        self.assertNotEqual(first.mc_employee_id, second.mc_employee_id)

    def test_empleado_es_opcional_sin_copiar_usuario_o_responsable(self):
        activity = self._activity()
        self.assertEqual(activity.user_id, self.taller)
        self.assertFalse(activity.mc_employee_id)
        self.assertEqual(activity.res_id, self.order.id)

    def test_asignar_nombre_publico_sin_conceder_rrhh_privado(self):
        activity = self._activity()
        public_employee = self.env["hr.employee.public"].with_user(self.taller)
        self.assertFalse(self.env["hr.employee"].with_user(self.taller).has_access("read"))
        self.assertEqual(public_employee.browse(self.pedro.id).name, self.pedro.name)
        activity.with_user(self.taller).write({"mc_employee_id": self.pedro.id})
        self.assertEqual(
            activity.with_user(self.taller).mc_employee_id.display_name, self.pedro.name
        )
        self.assertFalse(self.env["hr.employee"].with_user(self.taller).has_access("read"))

    def test_rechaza_nueva_asignacion_de_empleado_archivado(self):
        activity = self._activity()
        self.pedro.active = False
        with self.assertRaises(ValidationError), self.cr.savepoint():
            activity.write({"mc_employee_id": self.pedro.id})
        self.assertFalse(activity.mc_employee_id)

    def test_rechaza_empleado_de_otra_empresa(self):
        activity = self._activity()
        # La empresa es real; su proyecto interno de partes de horas no pertenece
        # a este contrato y en STAGING tiene una restricción billing_type residual.
        with patch.object(
            type(self.env["res.company"]), "_create_internal_project_task", create=True
        ):
            other_company = self.env["res.company"].create({"name": "QA otra empresa asignación"})
        other_employee = self.env["hr.employee"].create(
            {"name": "QA ejecutor externo", "company_id": other_company.id}
        )
        with self.assertRaises(ValidationError), self.cr.savepoint():
            activity.write({"mc_employee_id": other_employee.id})
        self.assertFalse(activity.mc_employee_id)

    def test_archivado_posterior_conserva_asignacion_sin_cambiar_orden(self):
        before = self.order.read(["user_id", "state", "write_date"])
        activity = self._activity(self.pedro)
        self.pedro.active = False
        activity.write({"summary": "QA descripción ajustada"})
        self.assertEqual(activity.mc_employee_id, self.pedro)
        self.assertEqual(activity.user_id, self.taller)
        self.assertEqual(self.order.read(["user_id", "state", "write_date"]), before)


class TestWorkAssignmentAccess(ActivityAssignmentCommon):
    """La consulta conserva el alcance personal y los permisos del origen."""

    def _service(self, user=None):
        self.assertIn(
            "mc.rov.work.assignment",
            self.env,
            "Missing work assignment service",
        )
        return self.env["mc.rov.work.assignment"].with_user(user or self.taller)

    def _action_ids(self, action):
        self.assertEqual(action["res_model"], "mail.activity")
        self.assertIsInstance(action["domain"], list)
        return self.env["mail.activity"].with_user(self.taller).search(action["domain"]).ids

    def _hide_order(self):
        self.env["ir.rule"].create(
            {
                "name": "QA origen restringido",
                "model_id": self.env["ir.model"]._get_id("repair.order"),
                "domain_force": str([("id", "!=", self.order.id)]),
            }
        )

    def test_personal_incluye_futuras_y_no_rov_solo_de_su_cuenta(self):
        service = self._service()
        own = self._activity(self.pedro)
        other = self._activity(self.ana)
        other.user_id = self.env.ref("base.user_admin")
        self.assertFalse(self.order.lot_id)
        ids = self._action_ids(service.action_activities())
        self.assertIn(own.id, ids)
        self.assertNotIn(other.id, ids)

    def test_equipo_exige_permiso_y_coordinacion_no_lo_concede(self):
        service = self._service()
        self.assertFalse(service.get_capabilities()["can_view_team"])
        with self.assertRaises(AccessError):
            service.action_activities(scope="team")
        self.taller.group_ids = [
            Command.link(self.env.ref("mc_rov.group_work_assignment_coordinate").id)
        ]
        caps = service.get_capabilities()
        self.assertTrue(caps["can_coordinate"])
        self.assertFalse(caps["can_view_team"])
        with self.assertRaises(AccessError):
            service.action_activities(scope="team")

    def test_filtro_empleado_no_cambia_cuenta_ni_acceso(self):
        service = self._service()
        pedro = self._activity(self.pedro)
        ana = self._activity(self.ana)
        ids = self._action_ids(service.action_activities(employee_id=self.pedro.id))
        self.assertIn(pedro.id, ids)
        self.assertNotIn(ana.id, ids)
        with self.assertRaises(AccessError):
            service.action_activities(user_id=self.env.ref("base.user_admin").id)
        with self.assertRaises(UserError):
            service.action_activities(scope="unknown")

    def test_empresa_fuera_del_contexto_no_entra_en_personal(self):
        service = self._service()
        own = self._activity()
        with patch.object(
            type(self.env["res.company"]), "_create_internal_project_task", create=True
        ):
            company = self.env["res.company"].create({"name": "QA origen otra empresa"})
        order = (
            self.env["repair.order"]
            .with_company(company)
            .create(
                {
                    "product_id": self.product.id,
                    "company_id": company.id,
                }
            )
        )
        other = self._activity()
        other.res_id = order.id
        ids = self._action_ids(service.action_activities())
        self.assertIn(own.id, ids)
        self.assertNotIn(other.id, ids)

    def test_origen_prohibido_no_se_lista_ni_abre(self):
        service = self._service()
        activity = self._activity()
        self._hide_order()
        self.assertNotIn(activity.id, self._action_ids(service.action_activities()))
        with self.assertRaises(AccessError):
            service.action_open_source(activity.id)

    def test_lectura_directa_no_expone_origen_prohibido_por_asignacion(self):
        activity = self._activity()
        self._hide_order()
        restricted = activity.with_user(self.taller)
        self.assertFalse(restricted.has_access("read"))
        with self.assertRaises(AccessError):
            restricted.read(["res_name", "summary"])

    def test_abrir_origen_usa_referencia_exacta(self):
        service = self._service()
        activity = self._activity()
        action = service.action_open_source(activity.id)
        self.assertEqual(action["res_model"], "repair.order")
        self.assertEqual(action["res_id"], self.order.id)
        self.assertEqual(action["view_mode"], "form")

    def test_tareas_y_proyectos_personales_conservan_semantica_nativa(self):
        service = self._service()
        if "project.task" not in self.env:
            self.skipTest("Proyecto no instalado")
        self.taller.group_ids = [Command.link(self.env.ref("project.group_project_user").id)]
        tasks = service.action_tasks()
        projects = service.action_projects()
        self.assertEqual(tasks["res_model"], "project.task")
        self.assertIn(("user_ids", "in", [self.taller.id]), tasks["domain"])
        self.assertEqual(projects["res_model"], "project.project")
        self.assertIn(("task_ids.user_ids", "in", [self.taller.id]), projects["domain"])
        with self.assertRaises(AccessError):
            service.action_tasks(scope="team")


class TestWorkAssignmentWizard(ActivityAssignmentCommon):
    """Repartir trabajo no modifica el proceso y no deja cambios parciales."""

    def _assignment_service(self, coordinate=True):
        service = self.env["mc.rov.work.assignment"].with_user(self.taller)
        self.assertTrue(hasattr(service, "action_assign"), "Missing assignment wizard action")
        if coordinate:
            self.taller.group_ids = [
                Command.link(self.env.ref("mc_rov.group_work_assignment_coordinate").id)
            ]
        return service

    def _wizard(self, activities, values=None):
        action = self._assignment_service().action_assign(activities.ids)
        self.assertEqual(action["res_model"], "mc.rov.activity.assignment.wizard")
        self.assertEqual(action["target"], "new")
        return (
            self.env[action["res_model"]]
            .with_user(self.taller)
            .with_context(action["context"])
            .create(values or {})
        )

    def test_coordinacion_abre_sin_conceder_consulta_de_equipo(self):
        service = self._assignment_service()
        activity = self._activity()
        self.assertFalse(service.get_capabilities()["can_view_team"])
        action = service.action_assign([activity.id])
        self.assertEqual(action["res_model"], "mc.rov.activity.assignment.wizard")

    def test_consulta_de_equipo_no_permite_repartir(self):
        service = self._assignment_service(coordinate=False)
        self.taller.group_ids = [
            Command.link(self.env.ref("mc_rov.group_work_assignment_team").id)
        ]
        with self.assertRaises(AccessError):
            service.action_assign([self._activity().id])

    def test_seleccion_con_origen_prohibido_se_rechaza_completa(self):
        service = self._assignment_service()
        forbidden = self._activity()
        allowed = self._activity()
        other_order = self.env["repair.order"].create({"product_id": self.product.id})
        allowed.res_id = other_order.id
        before = allowed.read(["user_id", "date_deadline", "mc_employee_id"])
        TestWorkAssignmentAccess._hide_order(self)
        with self.assertRaises(AccessError):
            service.action_assign([allowed.id, forbidden.id])
        self.assertEqual(allowed.read(["user_id", "date_deadline", "mc_employee_id"]), before)

    def test_reasignacion_multiple_solo_cambia_campos_marcados(self):
        self._assignment_service()
        activities = self._activity(self.pedro) | self._activity(self.ana)
        wizard = self._wizard(
            activities,
            {
                "apply_user": True,
                "user_id": self.env.ref("base.user_admin").id,
            },
        )
        wizard.action_apply()
        self.assertEqual(activities.mapped("user_id"), self.env.ref("base.user_admin"))
        self.assertEqual(activities.mapped("mc_employee_id"), self.pedro | self.ana)
        self.assertEqual(
            set(activities.mapped("date_deadline")), {fields.Date.to_date("2026-10-20")}
        )

    def test_quitar_empleado_es_distinto_de_no_modificar(self):
        self._assignment_service()
        activity = self._activity(self.pedro)
        wizard = self._wizard(activity, {"apply_employee": True, "employee_id": False})
        wizard.action_apply()
        self.assertFalse(activity.mc_employee_id)
        self.assertEqual(activity.user_id, self.taller)

    def test_reprogramacion_exige_motivo_y_registra_cuenta_autora(self):
        self._assignment_service()
        activity = self._activity()
        wizard = self._wizard(
            activity,
            {
                "apply_deadline": True,
                "date_deadline": "2026-10-25",
            },
        )
        with self.assertRaises(UserError), self.cr.savepoint():
            wizard.action_apply()
        self.assertEqual(activity.date_deadline, fields.Date.to_date("2026-10-20"))
        wizard.reason = "Esperando repuesto confirmado"
        wizard.action_apply()
        self.assertEqual(activity.date_deadline, fields.Date.to_date("2026-10-25"))
        messages = self.order.message_ids.filtered(
            lambda message: "Esperando repuesto confirmado" in str(message.body)
        )
        self.assertTrue(messages)
        self.assertEqual(messages[0].author_id, self.taller.partner_id)

    def test_empleado_archivado_rechaza_toda_la_reasignacion(self):
        self._assignment_service()
        activities = self._activity() | self._activity()
        wizard = self._wizard(
            activities,
            {
                "apply_user": True,
                "user_id": self.env.ref("base.user_admin").id,
                "apply_employee": True,
                "employee_id": self.pedro.id,
            },
        )
        self.pedro.active = False
        with self.assertRaises(ValidationError), self.cr.savepoint():
            wizard.action_apply()
        self.assertEqual(activities.mapped("user_id"), self.taller)
        self.assertFalse(activities.mapped("mc_employee_id"))

    def test_repartir_no_cierra_orden_ni_modifica_repuestos(self):
        self._assignment_service()
        self.assertFalse(self.env["ir.model"].with_user(self.taller).has_access("read"))
        activity = self._activity()
        before = self.order.read(["state", "fecha_entrega_real", "move_ids"])
        wizard = self._wizard(activity, {"apply_employee": True, "employee_id": self.pedro.id})
        wizard.action_apply()
        self.assertFalse(self.env["ir.model"].with_user(self.taller).has_access("read"))
        self.assertEqual(activity.mc_employee_id, self.pedro)
        self.assertEqual(self.order.read(["state", "fecha_entrega_real", "move_ids"]), before)


class TestWorkAssignmentActivityViews(ActivityAssignmentCommon):
    """La asignación se consulta en las vistas nativas sin abrir RRHH privado."""

    def _native_view(self, xmlid, view_type):
        view = (
            self.env["mail.activity"]
            .with_user(self.taller)
            .get_view(view_id=self.env.ref(xmlid).id, view_type=view_type)
        )
        return etree.fromstring(view["arch"])

    def test_lista_formulario_calendario_muestran_empleado_sin_abrir_rrhh(self):
        self.assertFalse(self.env["hr.employee"].with_user(self.taller).has_access("read"))
        for xmlid, view_type in (
            ("mail.mail_activity_view_tree_open_target", "list"),
            ("mail.mail_activity_view_form", "form"),
            ("mail.mail_activity_view_calendar", "calendar"),
        ):
            arch = self._native_view(xmlid, view_type)
            employee = arch.xpath("//field[@name='mc_employee_id']")
            self.assertTrue(employee, "Missing assignment activity view")
            self.assertTrue(arch.xpath("//field[@name='mc_employee_display']"))
            if view_type != "calendar":
                self.assertEqual(employee[0].get("readonly"), "1")
                self.assertIn("no_open", employee[0].get("options", ""))
            if view_type == "list":
                self.assertEqual(employee[0].get("column_invisible"), "1")
        activity = self._activity().with_user(self.taller)
        self.assertEqual(activity.mc_employee_display, "Sin empleado asignado")
        activity.write({"mc_employee_id": self.pedro.id})
        self.assertEqual(activity.mc_employee_display, self.pedro.name)
        self.env["ir.rule"].create(
            {
                "name": "QA nombre publico oculto",
                "model_id": self.env["ir.model"]._get_id("hr.employee.public"),
                "domain_force": repr([("id", "!=", self.pedro.id)]),
            }
        )
        activity.invalidate_recordset(["mc_employee_display"])
        self.assertEqual(activity.mc_employee_display, "Sin acceso al nombre")
        self.assertFalse(self.env["hr.employee"].with_user(self.taller).has_access("read"))

    def test_kanban_distingue_empleado_vacio_de_usuario(self):
        arch = self._native_view("mail.mail_activity_view_kanban_open_target", "kanban")
        self.assertTrue(
            arch.xpath("//field[@name='mc_employee_id']"), "Missing assignment activity view"
        )
        self.assertIn("Sin empleado asignado", " ".join(arch.itertext()))
        self.assertTrue(arch.xpath("//field[@name='user_id']"))
        self.assertTrue(arch.xpath("//button[@name='action_done']"))

    def test_busqueda_y_agrupacion_por_empleado_no_usan_creador(self):
        arch = self._native_view("mail.mail_activity_view_search", "search")
        self.assertTrue(
            arch.xpath("//field[@name='mc_employee_id']"), "Missing assignment activity view"
        )
        self.assertTrue(arch.xpath("//filter[contains(@context, 'mc_employee_id')]"))
        self.assertTrue(
            arch.xpath(
                "//filter[contains(@domain, 'mc_employee_id') and contains(@domain, 'False')]"
            )
        )
        self.assertTrue(arch.xpath("//filter[contains(@context, 'user_id')]"))


class TestWorkAssignmentSearchPrivacy(ActivityAssignmentCommon):
    """Las consultas nativas tampoco revelan actividades de orígenes prohibidos."""

    def _hidden_activity_model(self):
        activity = self._activity(self.pedro)
        self.env["ir.rule"].create(
            {
                "name": "QA origen oculto en consultas nativas",
                "model_id": self.env["ir.model"]._get_id("repair.order"),
                "domain_force": str([("id", "!=", self.order.id)]),
            }
        )
        return activity, self.env["mail.activity"].with_user(self.taller)

    def test_busqueda_directa_no_revela_id_de_origen_prohibido(self):
        activity, model = self._hidden_activity_model()
        self.assertFalse(
            model.search([("id", "=", activity.id)]),
            "Missing native activity search source protection",
        )

    def test_conteo_directo_no_revela_origen_prohibido(self):
        activity, model = self._hidden_activity_model()
        self.assertEqual(
            model.search_count([("id", "=", activity.id)]),
            0,
            "Missing native activity count source protection",
        )

    def test_agrupacion_directa_no_revela_origen_prohibido(self):
        activity, model = self._hidden_activity_model()
        self.assertFalse(
            model._read_group([("id", "=", activity.id)], ["user_id"], ["__count"]),
            "Missing native activity group source protection",
        )

    def _hide_employee_name(self):
        self.env["ir.rule"].create(
            {
                "name": "QA nombre restringido en vistas y auditoría",
                "model_id": self.env["ir.model"]._get_id("hr.employee.public"),
                "domain_force": repr([("id", "!=", self.pedro.id)]),
            }
        )
        self.env.invalidate_all()

    def test_vista_no_falla_al_leer_relacion_con_nombre_restringido(self):
        activity = self._activity(self.pedro)
        self._hide_employee_name()
        try:
            rows = activity.with_user(self.taller).read(["mc_employee_id", "mc_employee_display"])
        except AccessError:
            self.fail("Missing native employee safe view serialization")
        self.assertEqual(rows[0]["mc_employee_display"], "Sin acceso al nombre")
        self.assertNotIn(self.pedro.name, str(rows))
        web_rows = activity.with_user(self.taller).web_read(
            {"mc_employee_id": {"fields": {"id": {}, "display_name": {}}}}
        )
        self.assertNotIn(self.pedro.name, str(web_rows))
        self.assertEqual(web_rows[0]["mc_employee_id"]["display_name"], "Sin acceso al nombre")

    def test_quitar_empleado_restringido_no_publica_nombre_en_auditoria(self):
        activity = self._activity(self.pedro)
        self.taller.group_ids = [
            Command.link(self.env.ref("mc_rov.group_work_assignment_coordinate").id)
        ]
        self._hide_employee_name()
        wizard = (
            self.env["mc.rov.activity.assignment.wizard"]
            .with_user(self.taller)
            .create(
                {
                    "activity_ids": [Command.set(activity.ids)],
                    "apply_employee": True,
                    "employee_id": False,
                }
            )
        )
        try:
            wizard.action_apply()
        except AccessError:
            self.fail("Missing native employee safe audit label")
        self.assertFalse(activity.mc_employee_id)
        message = self.order.message_ids.sorted("id", reverse=True)[0]
        self.assertNotIn(self.pedro.name, str(message.body))

    def test_agrupacion_empleado_no_expone_nombre_restringido(self):
        activity = self._activity(self.pedro)
        self._hide_employee_name()
        try:
            groups = (
                self.env["mail.activity"]
                .with_user(self.taller)
                .read_group([("id", "=", activity.id)], ["mc_employee_id"], ["mc_employee_id"])
            )
        except AccessError:
            self.fail("Missing native employee safe group label")
        self.assertNotIn(self.pedro.name, str(groups))
        web_groups = (
            self.env["mail.activity"]
            .with_user(self.taller)
            .web_read_group([("id", "=", activity.id)], ["mc_employee_id"])
        )
        self.assertNotIn(self.pedro.name, str(web_groups))
        self.assertIn("Sin acceso al nombre", str(web_groups))

    def test_pagina_se_aplica_despues_del_permiso_de_origen(self):
        forbidden = self._activity()
        visible_order = self.order.copy()
        first = self._activity()
        second = self._activity()
        (first | second).write({"res_id": visible_order.id})
        self.env["ir.rule"].create(
            {
                "name": "QA paginacion tras permiso del origen",
                "model_id": self.env["ir.model"]._get_id("repair.order"),
                "domain_force": repr([("id", "!=", self.order.id)]),
            }
        )
        model = self.env["mail.activity"].with_user(self.taller)
        domain = [("id", "in", (forbidden | first | second).ids)]
        self.assertEqual(model.search(domain, limit=1, order="id"), first.with_user(self.taller))
        self.assertEqual(
            model.search(domain, offset=1, limit=1, order="id"), second.with_user(self.taller)
        )

    def test_exportacion_solo_muestra_nombre_publico_autorizado(self):
        activity = self._activity(self.pedro)
        self._hide_employee_name()
        with self.assertRaises(UserError):
            activity.with_user(self.taller).export_data(["mc_employee_id"])
        self.taller.write(
            {"group_ids": [Command.link(self.env.ref("base.group_allow_export").id)]}
        )
        for user in (self.taller, self.env.ref("base.user_admin")):
            exported = activity.with_user(user).export_data(["mc_employee_id"])
            self.assertNotIn(self.pedro.name, str(exported))
            self.assertIn("Sin acceso al nombre", str(exported))
            with self.assertRaises(ValidationError):
                activity.with_user(user).export_data(["mc_employee_id/name"])
        self.env["ir.rule"].create(
            {
                "name": "QA origen no exportable",
                "model_id": self.env["ir.model"]._get_id("repair.order"),
                "domain_force": repr([("id", "!=", self.order.id)]),
            }
        )
        with self.assertRaises(AccessError):
            activity.with_user(self.taller).export_data(["summary"])
