from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.addons.hr.models.hr_employee import _ALLOW_READ_HR_EMPLOYEE
from odoo.exceptions import ValidationError
from odoo.tools import SQL


class MailActivity(models.Model):
    """Añade la persona ejecutora sin sustituir la cuenta asignada ni su autoría."""

    _inherit = "mail.activity"

    mc_employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado asignado",
        ondelete="set null",
        index=True,
        exportable=False,
        domain="[('active', '=', True)]",
        help="Persona que realizará esta actividad; puede usar una cuenta compartida.",
    )
    mc_employee_display = fields.Char(
        string="Empleado asignado",
        compute="_compute_mc_employee_display",
        compute_sudo=False,
    )

    @api.depends("mc_employee_id")
    @api.depends_context("uid", "company")
    def _compute_mc_employee_display(self):
        # La etiqueta usa el directorio público y permisos de quien consulta;
        # un nombre no accesible no se sustituye por información privada de RRHH.
        names = self._mc_public_employee_names(self.mapped("mc_employee_id").ids)
        for activity in self:
            employee_id = activity.mc_employee_id.id
            activity.mc_employee_display = (
                names.get(employee_id, _("Sin acceso al nombre"))
                if employee_id
                else _("Sin empleado asignado")
            )

    def _mc_public_employee_names(self, employee_ids):
        public = self.env["hr.employee.public"].with_context(active_test=False)
        if not public.has_access("read"):
            return {}
        return {
            employee.id: employee.display_name
            for employee in public.search([("id", "in", list(employee_ids))])
        }

    # Firma nativa de Odoo: conservar los argumentos para consultas y fetch.
    @api.model
    def _search(
        self, domain, offset=0, limit=None, order=None, *, bypass_access=False, **kwargs
    ):  # pylint: disable=too-many-arguments
        # La asignación a una cuenta no autoriza el documento. Filtrar antes
        # de paginar mantiene iguales los límites de lista, conteo y agrupación.
        if self.env.su or bypass_access:
            return super()._search(
                domain, offset, limit, order, bypass_access=bypass_access, **kwargs
            )
        query = super()._search(domain, 0, None, order, **kwargs)
        ids = [row[0] for row in self.env.execute_query(query.select())]
        allowed = self.browse(ids)._mc_source_readable_ids()
        query.add_where(SQL("%s = ANY(%s)", SQL.identifier(query.table, "id"), allowed))
        query.offset = offset
        query.limit = limit
        return query

    def _read_format(self, fnames, load="_classic_read"):
        if "mc_employee_id" not in fnames or load != "_classic_read":
            return super()._read_format(fnames, load=load)
        # El convertidor Many2one nativo usa el nombre privado con sudo.
        # Formatear solo esta relación desde el directorio público autorizado.
        rows = super()._read_format(
            [name for name in fnames if name != "mc_employee_id"], load=load
        )
        labels = {
            activity.id: (
                (activity.mc_employee_id.id, activity.mc_employee_display)
                if activity.mc_employee_id
                else False
            )
            for activity in self
        }
        for row in rows:
            row["mc_employee_id"] = labels[row["id"]]
        return rows

    def web_read(self, specification):
        self.check_access("read")
        employee_spec = specification.get("mc_employee_id", {})
        if "fields" not in employee_spec:
            return super().web_read(specification)
        requested = employee_spec["fields"]
        if set(requested) - {"id", "display_name"}:
            raise ValidationError(_("La actividad solo muestra el nombre público del empleado."))
        # web_read también serializa Many2one por una ruta distinta de read.
        safe_specification = dict(specification, mc_employee_id={})
        rows = super().web_read(safe_specification)
        labels = {activity.id: activity.mc_employee_display for activity in self}
        for row in rows:
            employee_id = row["mc_employee_id"]
            if employee_id:
                row["mc_employee_id"] = {"id": employee_id}
                if "display_name" in requested:
                    row["mc_employee_id"]["display_name"] = labels[row["id"]]
        return rows

    def export_data(self, fields_to_export):
        self.check_access("read")
        if any(name.startswith("mc_employee_id/") for name in fields_to_export):
            raise ValidationError(_("Exporte el nombre público desde Empleado asignado."))
        # La exportación nativa convierte relaciones sin pasar por read/web_read.
        return super().export_data(
            [
                "mc_employee_display" if name == "mc_employee_id" else name
                for name in fields_to_export
            ]
        )

    @api.model
    def _read_group_format_result(self, rows_dict, lazy_groupby):
        employee_groups = [group for group in lazy_groupby if group == "mc_employee_id"]
        super()._read_group_format_result(
            rows_dict, [group for group in lazy_groupby if group not in employee_groups]
        )
        if employee_groups:
            names = self._mc_public_employee_names(
                row["mc_employee_id"].id for row in rows_dict if row["mc_employee_id"]
            )
            for row in rows_dict:
                employee_id = row["mc_employee_id"].id or False
                row["mc_employee_id"] = (
                    (employee_id, names.get(employee_id, _("Sin acceso al nombre")))
                    if employee_id
                    else False
                )
                row["__domain"] = Domain(row["__domain"]) & Domain(
                    "mc_employee_id", "=", employee_id
                )

    def _web_read_group_groupby_formatter(self, groupby_spec, values):
        if groupby_spec != "mc_employee_id":
            return super()._web_read_group_groupby_formatter(groupby_spec, values)
        names = self._mc_public_employee_names(value.id for value in values if value)

        def formatter(value):
            employee_id = value.id or False
            label = (
                (employee_id, names.get(employee_id, _("Sin acceso al nombre")))
                if employee_id
                else False
            )
            return label, [("mc_employee_id", "=", employee_id)]

        return formatter

    def _mc_source_readable_ids(self):
        """Valida orígenes sin leer nombres de actividades todavía no autorizadas."""
        if not self:
            return []
        self.flush_recordset(["res_model", "res_id"])
        # Leer solo referencias evita recursión en _check_access; no se elevan
        # permisos ni se devuelve esta metadata por RPC. El origen usa el ORM.
        rows = self.env.execute_query(
            SQL(
                "SELECT id, res_model, res_id FROM mail_activity WHERE id = ANY(%s)",
                self.ids,
            )
        )
        grouped = {}
        allowed = []
        for activity_id, model, res_id in rows:
            if not model and not res_id:
                allowed.append(activity_id)
            elif model in self.env and res_id:
                grouped.setdefault(model, []).append((activity_id, res_id))
        companies = self.env.companies.ids
        for model, references in grouped.items():
            documents = self.env[model].browse(list({res_id for _, res_id in references}))
            documents = documents.exists()._filtered_access("read")
            if "company_id" in documents._fields:
                documents = documents.filtered(
                    lambda doc: not doc.company_id or doc.company_id.id in companies
                )
            document_ids = set(documents.ids)
            allowed.extend(act_id for act_id, res_id in references if res_id in document_ids)
        return allowed

    def _check_access(self, operation):
        result = super()._check_access(operation)
        if operation != "read" or not self or self.env.su:
            return result
        candidates = self - result[0] if result else self
        # onchange wraps Many2many entries in NewId(origin=...). SQL validates
        # saved origins; match permissions back to their temporary counterparts.
        allowed_ids = set(candidates._origin._mc_source_readable_ids())
        forbidden = candidates.filtered(lambda record: record._origin.id not in allowed_ids)
        for record in candidates - forbidden:
            if record == record._origin:
                continue
            # A modified temporary reference must not borrow the old origin's
            # permission to expose a different document.
            model, res_id = record.res_model, record.res_id
            if not model and not res_id:
                continue
            if model not in self.env or not res_id:
                forbidden |= record
                continue
            document = self.env[model].browse(res_id).exists()._filtered_access("read")
            if not document or (
                "company_id" in document._fields
                and document.company_id
                and document.company_id.id not in self.env.companies.ids
            ):
                forbidden |= record
        if not forbidden:
            return result
        if result:
            return (result[0] | forbidden, result[1])
        return (forbidden, lambda: forbidden._make_access_error(operation))

    # Conservar fields como keyword mantiene la firma de la API nativa.
    def read(self, fields=None, load="_classic_read"):  # pylint: disable=redefined-outer-name
        # read puede reutilizar valores prefetched; verificar también aquí para
        # que una caché poblada por otra cuenta no sustituya el permiso del origen.
        self.check_access("read")
        return super().read(fields=fields, load=load)

    def _mc_assignment_company(self, values):
        model = values.get("res_model", self.res_model if self else False)
        if values.get("res_model_id"):
            # Resolver la referencia técnica no exige conceder el catálogo de
            # administración; el documento resultante sí conserva su control ORM.
            rows = self.env.execute_query(
                SQL("SELECT model FROM ir_model WHERE id = %s", values["res_model_id"])
            )
            model = rows[0][0] if rows else False
        elif "res_model_id" in values:
            model = values.get("res_model")
        res_id = values.get("res_id", self.res_id if self else False)
        if model and res_id:
            source = self.env[model].browse(res_id).exists()
            source.check_access("read")
            if source and "company_id" in source._fields:
                return source.company_id
        return self.env.company

    def _mc_validate_employee(self, employee_id, values, new_assignment=True):
        if not employee_id:
            return
        # La selección y la validación usan solo el directorio público, con sus reglas.
        employee = (
            self.env["hr.employee.public"]
            .with_context(active_test=False)
            .search([("id", "=", employee_id)], limit=1)
        )
        if not employee:
            raise ValidationError(_("El empleado seleccionado no está disponible."))
        if new_assignment and not employee.active:
            raise ValidationError(_("No se puede asignar una actividad a un empleado archivado."))
        company = self._mc_assignment_company(values)
        if company and employee.company_id != company:
            raise ValidationError(_("El empleado debe pertenecer a la empresa del registro."))

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(["mc_employee_id", "res_model_id", "res_model", "res_id"])
        for values in vals_list:
            effective = defaults | values
            self._mc_validate_employee(effective.get("mc_employee_id"), effective)
        # Odoo 19 exige lectura del comodel al escribir relaciones. El token nativo
        # se limita a esta operación tras validar el empleado por su perfil público;
        # no concede ACL de RRHH ni se devuelve en el entorno de los registros.
        relation_model = self
        if any((defaults | values).get("mc_employee_id") for values in vals_list):
            relation_model = self.with_context(_allow_read_hr_employee=_ALLOW_READ_HR_EMPLOYEE)
        activities = super(MailActivity, relation_model).create(vals_list)
        return activities.with_env(self.env)

    def write(self, values):
        if {"mc_employee_id", "res_id", "res_model_id"}.intersection(values):
            self.check_access("write")
            for activity in self:
                employee_id = values.get("mc_employee_id", activity.mc_employee_id.id)
                activity._mc_validate_employee(
                    employee_id,
                    values,
                    new_assignment=employee_id != activity.mc_employee_id.id,
                )
        if values.get("mc_employee_id"):
            return super(
                MailActivity, self.with_context(_allow_read_hr_employee=_ALLOW_READ_HR_EMPLOYEE)
            ).write(values)
        return super().write(values)
