from odoo import _, api, models
from odoo.exceptions import AccessError, UserError
from odoo.osv import expression
from odoo.tools import is_html_empty
from odoo.tools.safe_eval import safe_eval


DEFINITIONS = {
    ("repair", "orders"): (
        "repair.order",
        "repair.action_repair_order_tree",
        "product_id.product_tmpl_id",
        "state",
    ),
    ("repair", "reviews"): (
        "mc.rov.revision",
        "mc_rov.action_mc_rov_prueba_realizada",
        "lot_id.product_id.product_tmpl_id",
        "estado",
    ),
    ("manufacturing", "manufacturing"): (
        "mrp.production",
        "mrp.mrp_production_action",
        "product_id.product_tmpl_id",
        "state",
    ),
    ("acceptance", "equipment"): (
        "stock.lot",
        "stock.action_production_lot_form",
        "product_id.product_tmpl_id",
        "mc_estado_operativo",
    ),
    ("acceptance", "performance"): (
        "mc.rov.revision",
        "mc_rov.action_mc_rov_prueba_realizada",
        "lot_id.product_id.product_tmpl_id",
        "estado",
    ),
    ("acceptance", "field"): (
        "mc.rov.revision",
        "mc_rov.action_mc_rov_prueba_realizada",
        "lot_id.product_id.product_tmpl_id",
        "estado",
    ),
    ("acceptance", "fen"): (
        "mc.rov.ficha.equipo.nuevo",
        None,
        "lot_id.product_id.product_tmpl_id",
        "estado",
    ),
    ("equipment", "equipment"): (
        "stock.lot",
        "stock.action_production_lot_form",
        "product_id.product_tmpl_id",
        "mc_estado_operativo",
    ),
    ("quality", "alerts"): (
        "quality.alert",
        "quality_control.quality_alert_action_check",
        "product_tmpl_id",
        "stage_id",
    ),
    ("quality", "checks"): (
        "quality.check",
        "quality_control.quality_check_action_main",
        "product_id.product_tmpl_id",
        "quality_state",
    ),
    ("quality", "lessons"): (
        "quality.alert",
        "quality_control.quality_alert_action_check",
        "product_tmpl_id",
        "stage_id",
    ),
    ("design", "models"): (
        "product.template",
        "mrp.product_template_action",
        None,
        None,
    ),
    ("design", "bom"): (
        "mrp.bom",
        "mrp.mrp_bom_form_action",
        "product_tmpl_id",
        None,
    ),
    ("design", "changes"): (
        "mrp.eco",
        "mrp_plm.mrp_eco_action_main",
        "product_tmpl_id",
        "state",
    ),
}


REVISION_TYPES = {"reviews": "reparacion", "performance": "rendimiento", "field": "terreno"}
EQUIPMENT_STATES = ("Operativo", "En mantención", "En reparación")

# Reuse operational ownership only: product.responsible_id concerns logistics, not design.
RESPONSIBLE_FIELDS = {
    "repair.order": "user_id",
    "mrp.production": "user_id",
    "quality.alert": "user_id",
    "quality.check": "user_id",
    "mrp.eco": "user_id",
    "mc.rov.revision": "responsable_id",
    "mc.rov.ficha.equipo.nuevo": "responsable_id",
}


class WorkCenter(models.AbstractModel):
    """Consulta trabajo ROV y abre sus formularios, sin crear estados de proceso."""

    _name = "mc.rov.work.center"
    _description = "Centro de trabajo ROV"

    def _get_definition(self, topic, kind):
        if not self.env.user.has_group("base.group_user"):
            raise AccessError(_("El centro requiere un usuario interno."))
        if not isinstance(topic, str) or not isinstance(kind, str):
            raise UserError(_("Área o tipo de registro no válido."))
        definition = DEFINITIONS.get((topic, kind))
        if not definition:
            raise UserError(_("Área o tipo de registro no válido."))
        return definition

    def _native_action(self, definition, kind):
        model, xmlid, _model_path, _state = definition
        if xmlid:
            action = self.env["ir.actions.actions"]._for_xml_id(xmlid)
        else:
            action = {"type": "ir.actions.act_window", "name": _("Fichas"), "res_model": model}
        values = {
            "uid": self.env.uid,
            "user": self.env.user,
            "allowed_company_ids": self.env.companies.ids,
            "context": dict(self.env.context),
        }
        for field in ("context", "domain"):
            value = action.get(field) or ({} if field == "context" else [])
            if isinstance(value, str):
                value = safe_eval(value, values)
            action[field] = value
        # Las búsquedas nativas por defecto no deben contradecir el filtro elegido.
        action["context"] = {
            key: value
            for key, value in action["context"].items()
            if not key.startswith("search_default_")
        }
        if model == "mc.rov.revision":
            # La acción compartida propone RND; cada entrada debe conservar su tipo.
            action["context"]["default_tipo"] = REVISION_TYPES[kind]
        action["view_mode"] = "list,form"
        action["views"] = [(False, "list"), (False, "form")]
        action["target"] = "current"
        return action

    # Los argumentos reflejan los filtros compartidos por las llamadas RPC.
    # pylint: disable-next=too-many-arguments
    def _get_domain(self, topic, kind, state_filter="open", query="", model_id=False):
        definition = self._get_definition(topic, kind)
        model_name, _xmlid, model_path, state_field = definition
        valid_states = ("open", "all") + (EQUIPMENT_STATES if model_name == "stock.lot" else ())
        if state_filter not in valid_states:
            raise UserError(_("Filtro de estado no válido."))
        if not isinstance(query, str) or len(query) > 100:
            raise UserError(_("La búsqueda admite hasta 100 caracteres."))
        if model_id is not False and (
            not isinstance(model_id, int) or isinstance(model_id, bool) or model_id <= 0
        ):
            raise UserError(_("Modelo de equipo no válido."))
        model = self.env[model_name]
        model.check_access("read")
        root = self.env["stock.lot"]._get_rov_root_category()
        if not root:
            raise UserError(_("No está configurada la categoría raíz ROV."))
        domain = expression.AND(
            [
                self._native_action(definition, kind)["domain"],
                self._rov_scope(model_name, model_path, root),
            ]
        )
        domain = expression.AND([domain, self._company_scope(model)])
        if model_name == "mc.rov.revision":
            domain = expression.AND([domain, [("tipo", "=", REVISION_TYPES[kind])]])
            if topic == "acceptance":
                domain = expression.AND([domain, [("repair_id", "=", False)]])
        domain = self._state_domain(model, domain, state_field, state_filter, kind)
        if model_id:
            self.env["product.template"].browse(model_id).check_access("read")
            domain = expression.AND([domain, [(model_path or "id", "=", model_id)]])
        if query.strip():
            domain = expression.AND([domain, self._query_scope(model, model_path, query.strip())])
        return definition, domain

    def _query_scope(self, model, model_path, query):
        """Busca la referencia y el modelo usando los mismos términos en cada acceso."""
        reference_field = "name" if "name" in model._fields else "code"
        terms = [[(reference_field, "ilike", query)]]
        if model_path:
            terms.append([(model_path + ".name", "ilike", query)])
        return expression.OR(terms)

    def _rov_scope(self, model_name, model_path, root):
        """Acota cada tipo a equipos ROV sin ampliar el catálogo de diseño."""
        if model_name == "stock.lot":
            scope = [("es_un_rov", "=", True)]
        elif model_name in ("quality.alert", "quality.check"):
            scope = expression.OR(
                [
                    [("product_id.categ_id", "child_of", root.id)],
                    [("lot_ids.product_id.categ_id", "child_of", root.id)],
                ]
            )
            if model_name == "quality.alert":
                scope = expression.OR([scope, [("product_tmpl_id.categ_id", "child_of", root.id)]])
        else:
            category_path = "categ_id" if model_path is None else model_path + ".categ_id"
            scope = [(category_path, "child_of", root.id)]
        return scope

    def _company_scope(self, model):
        """Los documentos sin compañía propia heredan el alcance de su unidad."""
        if "company_id" in model._fields:
            return [("company_id", "in", self.env.companies.ids + [False])]
        if model._name in ("mc.rov.revision", "mc.rov.ficha.equipo.nuevo"):
            return [("lot_id.company_id", "in", self.env.companies.ids + [False])]
        return []

    # El dominio y sus filtros se mantienen juntos para preservar la equivalencia de listas.
    # pylint: disable-next=too-many-arguments
    def _state_domain(self, model, domain, state_field, state_filter, kind):
        """Aplica estados operativos o de documento, y lecciones no vacías."""
        model_name = model._name
        if model_name == "stock.lot" and state_filter in EQUIPMENT_STATES:
            domain = expression.AND([domain, [(state_field, "=", state_filter)]])
        if kind == "lessons":
            domain = expression.AND([domain, [("stage_id.done", "=", True)]])
            # HTML vacío como <p><br></p> no constituye una lección preventiva.
            lessons = model.search(domain).filtered(
                lambda row: not is_html_empty(row.action_preventive)
            )
            domain = expression.AND([domain, [("id", "in", lessons.ids)]])
        elif state_filter == "open":
            if model_name in ("repair.order", "mrp.production"):
                domain = expression.AND([domain, [(state_field, "not in", ["done", "cancel"])]])
            elif model_name in ("mc.rov.revision", "mc.rov.ficha.equipo.nuevo"):
                domain = expression.AND([domain, [(state_field, "=", "borrador")]])
            elif model_name == "quality.alert":
                domain = expression.AND([domain, [("stage_id.done", "=", False)]])
            elif model_name == "quality.check":
                domain = expression.AND([domain, [("quality_state", "=", "none")]])
            elif model_name == "mrp.eco":
                domain = expression.AND([domain, [("state", "!=", "done")]])
        return domain

    @api.model
    def get_equipment_models(self, query="", offset=0):
        """Ofrece modelos de unidades visibles, también si su modelo fue archivado."""
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise UserError(_("Página no válida."))
        _definition, lot_domain = self._get_domain("equipment", "equipment", "all", query)
        if query.strip():
            # El selector busca modelos, no números de serie.
            _definition, lot_domain = self._get_domain("equipment", "equipment", "all")
            lot_domain = expression.AND(
                [
                    lot_domain,
                    [("product_id.product_tmpl_id.name", "ilike", query.strip())],
                ]
            )
        groups = self.env["stock.lot"]._read_group(lot_domain, ["product_id"], [])
        model_ids = [product.product_tmpl_id.id for (product,) in groups if product]
        model = self.env["product.template"].with_context(active_test=False)
        model.check_access("read")
        domain = [("id", "in", model_ids)]
        total = model.search_count(domain)
        records = model.search(domain, limit=20, offset=offset, order="name, id")
        return {
            "rows": [{"id": record.id, "reference": record.display_name} for record in records],
            "total": total,
            "next_offset": offset + 20 if offset + 20 < total else False,
        }

    @api.model
    # La firma RPC conserva los filtros y la paginación de la interfaz.
    # pylint: disable-next=too-many-arguments
    def get_records(self, topic, kind, state_filter="open", query="", model_id=False, offset=0):
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise UserError(_("Página no válida."))
        definition, domain = self._get_domain(topic, kind, state_filter, query, model_id)
        model = self.env[definition[0]]
        total = model.search_count(domain)
        records = model.search(domain, limit=20, offset=offset, order="id desc")
        return {
            "rows": self._record_rows(records, definition[2], definition[3]),
            "total": total,
            "next_offset": offset + 20 if offset + 20 < total else False,
            "responsible_label": (
                _("Técnico responsable")
                if model._name == "mc.rov.revision"
                else _("Responsable") if model._name in RESPONSIBLE_FIELDS else False
            ),
        }

    def _responsible_names(self, records):
        """Lee solo nombres permitidos; empleados públicos evitan exigir acceso privado a RRHH."""
        field_name = RESPONSIBLE_FIELDS.get(records._name)
        if not field_name:
            return False, {}
        ids = records.mapped(field_name).ids
        related_model = records._fields[field_name].comodel_name
        if related_model == "hr.employee":
            related_model = "hr.employee.public"
        related = self.env[related_model].with_context(active_test=False)
        if not ids or not related.has_access("read"):
            return field_name, {}
        # search_read aplica reglas en lote; no se expone la identidad del registro restringido.
        names = related.search_read([("id", "in", ids)], ["name"])
        return field_name, {row["id"]: row["name"] for row in names}

    def _record_rows(self, records, model_path, state_field):
        """Presenta referencias y estados nativos sin inferir tareas personales."""
        model = self.env[records._name]
        labels = {}
        if state_field and model._fields[state_field].type == "selection":
            labels = dict(model.fields_get([state_field])[state_field]["selection"])
        rows = []
        responsible_field, responsible_names = self._responsible_names(records)
        for record in records:
            related = record
            if model_path:
                for part in model_path.split("."):
                    related = related[part]
            state = record[state_field] if state_field else False
            if state and model._fields[state_field].type == "many2one":
                state = state.display_name
            responsible_id = record[responsible_field].id if responsible_field else False
            responsible = responsible_names.get(responsible_id, False)
            rows.append(
                {
                    "id": record.id,
                    "reference": record.display_name,
                    "context": related.display_name if model_path and related else "",
                    "state": labels.get(state, state) or "",
                    "responsible": responsible,
                    "responsible_state": (
                        "assigned"
                        if responsible
                        else "restricted" if responsible_id else "unassigned"
                    ),
                }
            )
        return rows

    @api.model
    def get_overview(self):
        result = []
        for (topic, kind), definition in DEFINITIONS.items():
            try:
                _definition, domain = self._get_domain(topic, kind)
                model = self.env[definition[0]]
                choose_equipment = topic == "acceptance" and kind != "equipment"
                create_model = self.env["stock.lot"] if choose_equipment else model
                result.append(
                    {
                        "topic": topic,
                        "kind": kind,
                        "available": True,
                        "count": model.search_count(domain),
                        "can_create": kind not in ("checks", "lessons")
                        and create_model.has_access("read" if choose_equipment else "create"),
                        "can_candidates": kind == "lessons"
                        and self.env["mc.rov.linea.falla"].has_access("read"),
                    }
                )
            except AccessError:
                result.append({"topic": topic, "kind": kind, "available": False})
        return result

    @api.model
    def action_candidates(self):
        """Abre la cola preventiva existente, conservando sus filtros y permisos."""
        self._get_definition("quality", "lessons")
        self.env["mc.rov.linea.falla"].check_access("read")
        root = self.env["stock.lot"]._get_rov_root_category()
        if not root:
            raise UserError(_("No está configurada la categoría raíz ROV."))
        action = self.env["ir.actions.actions"]._for_xml_id(
            "mc_rov.action_mc_rov_leccion_pendiente"
        )
        # La cola conserva «Pendientes» como filtro removible; no es una tarea nueva.
        if isinstance(action.get("context"), str):
            action["context"] = safe_eval(action["context"])
        domain = action.get("domain") or []
        if isinstance(domain, str):
            domain = safe_eval(domain)
        action["domain"] = expression.AND(
            [
                domain,
                [("repair_id.product_id.categ_id", "child_of", root.id)],
                [("repair_id.company_id", "in", self.env.companies.ids + [False])],
            ]
        )
        action["target"] = "current"
        return action

    @api.model
    # La lista nativa recibe los mismos filtros que la consulta del Centro.
    # pylint: disable-next=too-many-arguments
    def action_list(self, topic, kind, state_filter="all", query="", model_id=False):
        definition, domain = self._get_domain(topic, kind, state_filter, query, model_id)
        action = self._native_action(definition, kind)
        action["domain"] = domain
        return action

    @api.model
    def action_open(self, topic, kind, record_id):
        if not isinstance(record_id, int) or isinstance(record_id, bool) or record_id <= 0:
            raise UserError(_("Registro no válido."))
        definition, domain = self._get_domain(topic, kind, "all")
        model = self.env[definition[0]]
        record = model.browse(record_id)
        record.check_access("read")
        if not model.search_count(expression.AND([domain, [("id", "=", record_id)]])):
            raise AccessError(_("El registro no está disponible en esta sección."))
        action = self._native_action(definition, kind)
        action.update(res_id=record_id, view_mode="form", views=[(False, "form")])
        return action

    @api.model
    def action_create(self, topic, kind):
        definition, _domain = self._get_domain(topic, kind, "all")
        if topic == "acceptance" and kind != "equipment":
            # La prueba/ficha nace desde una unidad elegida, no de una serie implícita.
            return self.action_list("acceptance", "equipment")
        if kind in ("checks", "lessons"):
            raise UserError(_("Estos registros se gestionan desde su operación de origen."))
        self.env[definition[0]].check_access("create")
        action = self._native_action(definition, kind)
        action.pop("res_id", None)
        action.update(view_mode="form", views=[(False, "form")])
        return action
