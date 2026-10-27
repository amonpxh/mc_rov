from odoo import _, api, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.safe_eval import safe_eval


INVENTORY_DESTINATIONS = {
    "stock": {"section": "stock", "model": "stock.quant", "method": "action_inventory"},
    "products": {
        "section": "products",
        "model": "product.template",
        "xmlid": "stock.product_template_action_product",
    },
    "variants": {
        "section": "products",
        "model": "product.product",
        "xmlid": "stock.stock_product_normal_action",
        "groups": ("product.group_product_variant",),
    },
    "lots": {
        "section": "lots",
        "model": "stock.lot",
        "xmlid": "stock.action_production_lot_form",
        "groups": ("stock.group_production_lot",),
    },
    "receipts": {
        "section": "operations",
        "model": "stock.picking",
        "method": "get_action_picking_tree_incoming",
        "read_dependencies": ("stock.picking.type",),
    },
    "deliveries": {
        "section": "operations",
        "model": "stock.picking",
        "method": "get_action_picking_tree_outgoing",
        "read_dependencies": ("stock.picking.type",),
    },
    "internal": {
        "section": "operations",
        "model": "stock.picking",
        "method": "get_action_picking_tree_internal",
        "read_dependencies": ("stock.picking.type",),
        "groups": ("stock.group_stock_multi_locations",),
    },
    "counts": {"section": "operations", "model": "stock.quant", "method": "action_view_inventory"},
    "replenishment": {
        "section": "replenishment",
        "model": "stock.warehouse.orderpoint",
        "method": "action_open_orderpoints",
        "groups": ("stock.group_stock_manager",),
    },
}


class WorkCenterInventory(models.AbstractModel):
    """Conecta el taller con destinos nativos de Inventario sin gestionar stock paralelo."""

    _inherit = "mc.rov.work.center"

    def _inventory_workspace_user(self):
        return self.env.user.has_group("base.group_user") and self.env.user.has_group(
            "stock.group_stock_user"
        )

    def _require_inventory_workspace(self):
        if not self._inventory_workspace_user():
            raise AccessError(_("Necesita acceso interno a Inventario para abrir este espacio."))
        # Las acciones nativas pueden mantener quants o reglas: validar antes de invocarlas.
        if not self.env.companies:
            raise AccessError(_("Seleccione una empresa permitida para Inventario."))

    def _inventory_destination_available(self, definition):
        return (
            all(self.env.user.has_group(group) for group in definition.get("groups", ()))
            and self.env[definition["model"]].has_access("read")
            and all(
                self.env[model].has_access("read")
                for model in definition.get("read_dependencies", ())
            )
        )

    @api.model
    def get_inventory_destinations(self):
        """Expone capacidades; no consulta cantidades ni ejecuta mantenimiento nativo."""
        self._require_inventory_workspace()
        labels = {
            "stock": _("Existencias"),
            "products": _("Productos"),
            "variants": _("Variantes"),
            "lots": _("Series y lotes"),
            "receipts": _("Recepciones"),
            "deliveries": _("Entregas"),
            "internal": _("Traslados internos"),
            "counts": _("Conteos y ajustes"),
            "replenishment": _("Reabastecimiento"),
        }
        result = []
        for key, definition in INVENTORY_DESTINATIONS.items():
            available = self._inventory_destination_available(definition)
            result.append(
                {
                    "key": key,
                    "section": definition["section"],
                    "label": labels[key],
                    "available": available,
                    "can_create": available and self.env[definition["model"]].has_access("create"),
                }
            )
        return result

    def _inventory_native_action(self, action):
        action = dict(action)
        values = {
            "uid": self.env.uid,
            "user": self.env.user,
            "allowed_company_ids": self.env.companies.ids,
            "context": dict(self.env.context),
        }
        for field, empty in (("domain", []), ("context", {})):
            value = action.get(field) or empty
            action[field] = safe_eval(value, values) if isinstance(value, str) else value
        # Conservar defaults y vistas del destino sin ampliar la selección activa de empresas.
        action["context"] = {
            **self.env.context,
            **action["context"],
            "allowed_company_ids": self.env.companies.ids,
        }
        return action

    @api.model
    def action_inventory_destination(self, key):
        """Abre solo destinos auditados con el usuario, permisos y contexto actuales."""
        self._require_inventory_workspace()
        if not isinstance(key, str) or key not in INVENTORY_DESTINATIONS:
            raise UserError(_("Destino de Inventario no válido."))
        definition = INVENTORY_DESTINATIONS[key]
        if not self._inventory_destination_available(definition):
            raise AccessError(_("No tiene acceso a este destino de Inventario."))
        if key == "stock":
            action = self.action_inventory()
        elif "xmlid" in definition:
            action = self.env["ir.actions.actions"]._for_xml_id(definition["xmlid"])
        else:
            model = self.env[definition["model"]]
            if key == "replenishment":
                # El menú nativo exige responsable; no basta la ACL de lectura de orderpoints.
                model = model.with_context(
                    search_default_filter_to_reorder=True,
                    search_default_filter_not_snoozed=True,
                    default_trigger="manual",
                    searchpanel_default_trigger="manual",
                )
            action = getattr(model, definition["method"])()
        return self._inventory_native_action(action)

    @api.model
    def get_inventory_application(self):
        """El cliente selecciona la aplicación mediante sus menús nativos autorizados."""
        self._require_inventory_workspace()
        return {"menu_id": self.env.ref("stock.menu_stock_root").id}

    @api.model
    def get_overview(self):
        result = super().get_overview()
        # El catálogo puede seguir permitido aunque el usuario no pueda consultar quants.
        available = self._inventory_workspace_user() and any(
            entry["available"] for entry in self.get_inventory_destinations()
        )
        for entry in result:
            if entry["topic"] == "inventory":
                entry["available"] = available
        return result
