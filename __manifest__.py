{
    "name": "Marine Connection - ROV",
    "version": "19.0.12.0.1",
    "category": "Inventory",
    "summary": "Gestión de equipos ROV y órdenes de reparación",
    "author": "Marine Connection",
    # hr entra en 19.0.8.0.0: el responsable de una revisión es un empleado y no un usuario,
    # porque los técnicos no tienen login propio —las licencias se pagan por usuario— y
    # porque quién hizo el trabajo y quién lo tecleó son dos cosas distintas.
    "depends": [
        "stock",
        "repair",
        "sale",
        "sale_renting",
        "hr",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mc_rov_data.xml",
        # Después de mc_rov_data.xml: marca como inspeccionables componentes definidos allí.
        "data/mc_rov_revision_data.xml",
        "views/mc_rov_componente_views.xml",
        "views/mc_rov_tipo_intervencion_views.xml",
        "views/mc_rov_revision_views.xml",
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
