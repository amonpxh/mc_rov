from odoo import _, api, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.safe_eval import safe_eval


# El origen inmediato identifica el contexto; no el título ni relaciones indirectas.
_PROCESS_MODELS = {
    "repair": ("repair.order",),
    "manufacturing": ("mrp.production",),
    "equipment": ("stock.lot",),
    "quality": ("quality.alert", "quality.check"),
    "design": ("product.template", "product.product", "mrp.bom", "mrp.eco"),
}


class McRovWorkAssignment(models.AbstractModel):
    """Consulta trabajo asignado sin sustituir los registros ni permisos nativos."""

    _name = "mc.rov.work.assignment"
    _description = "Consulta de trabajo asignado"

    @api.model
    def get_capabilities(self):
        self._check_internal_user()
        return {
            "can_view_team": self.env.user.has_group("mc_rov.group_work_assignment_team"),
            "can_coordinate": self.env.user.has_group("mc_rov.group_work_assignment_coordinate"),
        }

    def _check_internal_user(self):
        if not self.env.user.has_group("base.group_user"):
            raise AccessError(_("Este acceso requiere una cuenta interna."))

    def _check_scope(self, scope):
        self._check_internal_user()
        if scope not in ("mine", "team"):
            raise UserError(_("El alcance debe ser personal o de equipo."))
        if scope == "team" and not self.get_capabilities()["can_view_team"]:
            raise AccessError(_("No tiene permiso para consultar el trabajo del equipo."))

    @api.model
    def get_processes(self, kind="activities"):
        self._check_internal_user()
        if kind not in ("activities", "tasks", "projects"):
            raise ValidationError(_("El tipo de trabajo no es válido."))
        labels = {
            "all": _("Todos los procesos"),
            "repair": _("Reparación"),
            "manufacturing": _("Fabricación"),
            "acceptance": _("Aceptación"),
            "equipment": _("Equipo"),
            "quality": _("Calidad"),
            "design": _("Diseño"),
            "none": _("Sin proceso vinculado"),
        }
        options = []
        for key, label in labels.items():
            available = key in ("all", "none") or (kind == "activities" and key in _PROCESS_MODELS)
            hint = ""
            if not available:
                hint = (
                    _("RND/TRN y FEN aún no admiten actividades nativas específicas.")
                    if kind == "activities" and key == "acceptance"
                    else _("Las tareas y proyectos aún no tienen un vínculo directo al proceso.")
                )
            options.append({"key": key, "label": label, "available": available, "hint": hint})
        return options

    def _process_domain(self, process, kind):
        if process not in ("all", "none", "acceptance", *_PROCESS_MODELS):
            raise ValidationError(_("El proceso seleccionado no es válido."))
        if process == "all":
            return []
        # Los vínculos de Proyecto y las actividades de aceptación no se inventan
        # para completar un filtro: su implementación pertenece a otra entrega.
        if kind != "activities":
            return [] if process == "none" else [("id", "=", False)]
        if process == "acceptance":
            return [("id", "=", False)]
        if process == "none":
            known = [
                model
                for models_in_process in _PROCESS_MODELS.values()
                for model in models_in_process
            ]
            return [("res_model", "not in", known)]
        return [("res_model", "in", _PROCESS_MODELS[process])]

    def _native_action(self, xmlid, model, domain):
        if model not in self.env:
            raise UserError(_("La aplicación requerida no está instalada."))
        self.env[model].check_access("read")
        action = self.env["ir.actions.actions"]._for_xml_id(xmlid)
        native_domain = action.get("domain") or []
        if isinstance(native_domain, str):
            native_domain = safe_eval(
                native_domain, {"uid": self.env.uid, "context": self.env.context}
            )
        action["domain"] = native_domain + domain
        # Las actividades futuras forman parte del trabajo: no heredar los
        # filtros Hoy/Vencidas de Mis actividades ni active_ids de otra pantalla.
        action["context"] = {
            "lang": self.env.lang,
            "tz": self.env.user.tz,
            "allowed_company_ids": self.env.companies.ids,
        }
        return action

    @api.model
    def action_activities(self, scope="mine", employee_id=False, user_id=False, process="all"):
        self._check_scope(scope)
        if scope == "mine" and user_id and user_id != self.env.uid:
            raise AccessError(_("Mi trabajo solo permite consultar la cuenta actual."))
        domain = [("active", "=", True)] + self._process_domain(process, "activities")
        if scope == "mine" or user_id:
            domain.append(("user_id", "=", self.env.uid if scope == "mine" else user_id))
        if employee_id:
            employee = self.env["hr.employee.public"].search([("id", "=", employee_id)])
            if not employee:
                raise AccessError(_("El empleado seleccionado no está disponible."))
            domain.append(("mc_employee_id", "=", employee_id))
        # Keep the domain live for native create/reload. mail.activity._search
        # enforces source access before pagination on every subsequent query.
        return self._native_action("mail.mail_activity_action_my", "mail.activity", domain)

    @api.model
    def action_tasks(self, scope="mine", process="all"):
        self._check_scope(scope)
        domain = [("company_id", "in", [False] + self.env.companies.ids)] + self._process_domain(
            process, "tasks"
        )
        if scope == "mine":
            domain.append(("user_ids", "in", [self.env.uid]))
        return self._native_action("project.action_view_all_task", "project.task", domain)

    @api.model
    def action_projects(self, scope="mine", process="all"):
        self._check_scope(scope)
        domain = [("company_id", "in", [False] + self.env.companies.ids)] + self._process_domain(
            process, "projects"
        )
        if scope == "mine":
            domain.append(("task_ids.user_ids", "in", [self.env.uid]))
        return self._native_action("project.open_view_project_all", "project.project", domain)

    @api.model
    def action_open_source(self, activity_id):
        self._check_internal_user()
        activity = self.env["mail.activity"].browse(activity_id).exists()
        if not activity:
            raise UserError(_("La actividad ya no existe."))
        activity.check_access("read")
        if not activity.res_model or not activity.res_id:
            raise UserError(_("La actividad no está vinculada a un documento."))
        source = self.env[activity.res_model].browse(activity.res_id).exists()
        source.check_access("read")
        return {
            "type": "ir.actions.act_window",
            "res_model": source._name,
            "res_id": source.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def _assignment_activities(self, activity_ids):
        if not self.get_capabilities()["can_coordinate"]:
            raise AccessError(_("No tiene permiso para coordinar asignaciones."))
        if not activity_ids:
            raise UserError(_("Seleccione al menos una actividad."))
        activities = self.env["mail.activity"].browse(activity_ids).exists()
        if set(activities.ids) != set(activity_ids):
            raise UserError(_("Una actividad seleccionada ya no existe."))
        activities.check_access("read")
        activities.check_access("write")
        for activity in activities:
            if not activity.active:
                raise UserError(_("No se puede reasignar una actividad terminada."))
            if activity.res_model and activity.res_id:
                self.env[activity.res_model].browse(activity.res_id).check_access("write")
        return activities

    @api.model
    def action_assign(self, activity_ids):
        activities = self._assignment_activities(activity_ids)
        return {
            "type": "ir.actions.act_window",
            "name": _("Repartir actividades"),
            "res_model": "mc.rov.activity.assignment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_activity_ids": [(6, 0, activities.ids)],
                "allowed_company_ids": self.env.companies.ids,
            },
        }
