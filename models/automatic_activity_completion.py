from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class AutomaticActivityCompletion(models.Model):
    """Un aviso automático pendiente solo se cierra desde su trabajo real."""

    _inherit = "mail.activity"

    mc_automatic_pending = fields.Boolean(
        string="Seguimiento automático pendiente",
        compute="_compute_mc_automatic_pending",
        compute_sudo=False,
        readonly=True,
        exportable=False,
    )

    @api.depends("res_model", "res_id", "active")
    @api.depends_context("uid", "company")
    def _compute_mc_automatic_pending(self):
        # La presentación no usa los gateways de cierre: bloquean filas y
        # requieren escritura. Aquí basta la identidad con lectura autorizada.
        pending = self._mc_automatic_pending_ids()
        for activity in self:
            activity.mc_automatic_pending = activity.id in pending

    def _mc_automatic_pending_ids(self):
        activities = self.filtered(
            lambda row: isinstance(row.id, int)
            and not isinstance(row.id, bool)
            and row.id > 0
            and row.active
        )
        # Un onchange con NewId(origin=...) nunca hereda la identidad técnica
        # persistida. Validar el documento antes de consultar cualquier run.
        activities.check_access("read")
        companies = self.env.companies.ids
        pending = set()
        for flow, model, relation in (
            ("repair", "repair.order", "repair_id"),
            ("manufacturing", "mrp.production", "production_id"),
            ("acceptance", "stock.lot", "cycle_id.lot_id"),
            ("quality", "quality.alert", "alert_id"),
            ("engineering", "mrp.eco", "eco_id"),
            ("inventory", "stock.picking", "picking_id"),
        ):
            selected = activities.filtered_domain(
                [("res_model", "=", model), ("res_id", "!=", False)]
            )
            if not selected:
                continue
            sources = self.env[model].browse(selected.mapped("res_id")).exists()
            sources.check_access("read")
            if "company_id" in sources._fields and any(
                source.company_id and source.company_id.id not in companies for source in sources
            ):
                raise AccessError(_("El documento no pertenece a las empresas autorizadas."))
            runs = (
                self.env["mc.rov." + flow + ".activity.run"]
                .sudo()
                .search(
                    [
                        ("activity_id", "in", selected.ids),
                        ("outcome", "=", "pending"),
                        ("company_id", "in", companies),
                        (relation, "in", sources.ids),
                    ]
                )
            )
            pending.update(runs.activity_id.ids)
        return pending

    def _to_store_defaults(self, target):
        # También se autoriza en cada serialización: una caché previa no
        # sustituye los permisos actuales de usuario, origen y empresas.
        self.check_access("read")
        # El run puede vincularse después del create nativo de la actividad.
        # Serializar su identidad actual, no un False calculado durante create.
        self.invalidate_recordset(["mc_automatic_pending"])
        return super()._to_store_defaults(target) + ["mc_automatic_pending"]

    def _mc_check_automatic_completion(self):
        # Estos gateways validan actividad/origen y bloquean el seguimiento en
        # el mismo orden que su flujo. El nombre o tipo del aviso no autorizan
        # ni identifican un cierre, y un contexto RPC no permite saltárselo.
        for getter in (
            self._mc_repair_runs,
            self._mc_manufacturing_runs,
            self._mc_acceptance_runs,
            self._mc_quality_runs,
            self._mc_engineering_runs,
            self._mc_inventory_runs,
        ):
            if getter().filtered(lambda run: run.outcome == "pending"):
                raise UserError(
                    _(
                        "Esta actividad corresponde a trabajo automático pendiente. "
                        "Abra la operación y complétela o cancélela desde su proceso; "
                        "el aviso se cerrará automáticamente con el resultado real."
                    )
                )

    def _action_done(self, feedback=False, attachment_ids=None):
        with self.env.cr.savepoint():
            self._mc_check_automatic_completion()
            return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

    def action_cancel(self):
        with self.env.cr.savepoint():
            # El método nativo cancela uno por uno: validar el lote completo
            # antes de retirar una actividad manual que lo acompañe.
            self._mc_check_automatic_completion()
            return super().action_cancel()

    def unlink(self):
        with self.env.cr.savepoint():
            self._mc_check_automatic_completion()
            return super().unlink()

    def write(self, values):
        if "active" in values and not values["active"]:
            with self.env.cr.savepoint():
                self._mc_check_automatic_completion()
                return super().write(values)
        return super().write(values)
