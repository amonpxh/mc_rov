{
    "name": "Marine Connection - ROV",
    "version": "19.0.25.4.1",
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
        # mrp, quality_control y mrp_plm entran en 19.0.15.3.0, con los puentes a
        # quality.alert. Se evaluó un módulo puente aparte (mc_rov_quality) para no
        # arrastrarlos y se descartó: es mucha infraestructura para cuatro campos en un
        # módulo de una sola empresa. El costo aceptado es que mc_rov ya no se instala sin
        # Enterprise. Ver docs/pendientes.md, "Antes de empezar B".
        "mrp",
        "quality_control",
        "mrp_plm",
        # quality_mrp y quality_repair no estaban en el diseño y hacen falta: son ellos los
        # que definen quality.alert.production_id y quality.alert.repair_id, que es por
        # donde entran los puentes. Los dos son auto_install, así que ya estaban puestos —
        # pero declararlos fija el orden de carga, y sin eso mc_rov puede cargar antes que
        # el módulo que define los campos que extiende.
        "quality_mrp",
        "quality_repair",
    ],
    "data": [
        "security/work_assignment_groups.xml",
        "security/ir.model.access.csv",
        "security/repair_activity_policy_rules.xml",
        "security/automation_control_rules.xml",
        "security/manufacturing_activity_policy_rules.xml",
        "security/acceptance_activity_policy_rules.xml",
        "security/quality_activity_policy_rules.xml",
        "views/mc_rov_activity_assignment_wizard_views.xml",
        "views/mail_activity_views.xml",
        "data/mc_rov_data.xml",
        "data/repair_activity_types.xml",
        "data/manufacturing_activity_types.xml",
        "data/acceptance_activity_types.xml",
        "data/quality_activity_types.xml",
        # Después de mc_rov_data.xml: marca como inspeccionables componentes definidos allí.
        "data/mc_rov_revision_data.xml",
        "data/mc_rov_sintoma_data.xml",
        # Las causas de calidad, alineadas con ORIGENES. Sin dependencia de orden con lo
        # demás: el puente las busca por XML ID en tiempo de ejecución, no al cargar.
        "data/mc_rov_calidad_data.xml",
        "views/mc_rov_componente_views.xml",
        "views/mc_rov_sintoma_views.xml",
        "views/mc_rov_tipo_intervencion_views.xml",
        "views/mc_rov_revision_views.xml",
        "views/repair_order_views.xml",
        "views/stock_lot_views.xml",
        "views/mc_rov_ficha_equipo_nuevo_views.xml",
        "views/mc_rov_mantencion_views.xml",
        "views/mc_rov_propietario_views.xml",
        "views/mc_rov_baja_wizard_views.xml",
        # Los puentes a Calidad. Después de repair_order_views.xml porque el botón de
        # la línea de trabajo vive dentro de esa vista.
        "views/mc_rov_descarte_wizard_views.xml",
        "views/mc_rov_leccion_views.xml",
        "views/quality_alert_views.xml",
        "views/mrp_production_views.xml",
        "views/mrp_eco_views.xml",
        "views/product_template_views.xml",
        "views/mc_rov_menus.xml",
        "views/mc_rov_work_center_views.xml",
        "views/mc_rov_automation_control_views.xml",
        "views/mc_rov_repair_activity_policy_views.xml",
        "views/mc_rov_manufacturing_activity_policy_views.xml",
        "views/mc_rov_acceptance_activity_policy_views.xml",
        "views/mc_rov_quality_activity_policy_views.xml",
        "views/mc_rov_acceptance_evidence_wizard_views.xml",
        "reports/ficha_report.xml",
        "reports/ficha_equipo_nuevo_report.xml",
        "views/mc_rov_ficha_wizard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mc_rov/static/src/css/mc_rov.css",
            "mc_rov/static/src/work_center/assigned_work_view.js",
            "mc_rov/static/src/work_center/work_center.js",
            "mc_rov/static/src/work_center/work_center.xml",
            "mc_rov/static/src/work_center/work_center.scss",
        ],
        "web.assets_unit_tests": [
            "mc_rov/static/tests/work_center.test.js",
            "mc_rov/static/tests/embedded_work.test.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
