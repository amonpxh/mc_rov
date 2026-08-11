{
    "name": "Marine Connection - ROV",
    "version": "19.0.5.2.0",
    "category": "Inventory",
    "summary": "Gestión de equipos ROV y órdenes de reparación",
    "author": "Marine Connection",
    "depends": [
        "stock",
        "repair",
        "sale",
        "sale_renting",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mc_rov_data.xml",
        "views/mc_rov_componente_views.xml",
        "views/mc_rov_tipo_intervencion_views.xml",
        "views/repair_order_views.xml",
        "views/stock_lot_views.xml",
        "views/mc_rov_mantencion_views.xml",
        "views/mc_rov_propietario_views.xml",
        "views/mc_rov_baja_wizard_views.xml",
        "views/mc_rov_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mc_rov/static/src/css/mc_rov.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
