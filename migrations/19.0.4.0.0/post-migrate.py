import logging

_logger = logging.getLogger(__name__)

# Valor antiguo del Selection -> XML ID del registro mc.rov.tipo.intervencion que lo
# reemplaza. Los registros ya existen: los datos XML se cargan antes que post-migrate.
MAPEO_TIPOS = {
    "diagnostico": "tipo_diagnostico",
    "reparacion_correctiva": "tipo_reparacion_correctiva",
    "mantencion_preventiva": "tipo_mantencion_preventiva",
    "conversion": "tipo_conversion",
}


def migrate(cr, version):
    """Migra repair_order.tipo_intervencion (Selection varchar) a Many2many.

    Una visita al taller puede ser varias cosas a la vez —mantención que además
    descubre algo que reparar— y el Selection obligaba a elegir una. Cuando el técnico
    elegía "reparación", la mantención efectivamente hecha no quedaba registrada y el
    ciclo del equipo no se reiniciaba.

    Sigue el mismo patrón que 19.0.1.3.0, que migró linea_falla.accion a accion_id.
    Solo actúa si la columna antigua existe, para no correr en instalaciones frescas.
    """
    cr.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'repair_order' AND column_name = 'tipo_intervencion'
    """
    )
    if not cr.fetchone():
        return

    migradas = 0
    for valor_antiguo, xml_name in MAPEO_TIPOS.items():
        cr.execute(
            """
            INSERT INTO mc_rov_repair_order_tipo_rel (repair_order_id, tipo_id)
            SELECT ro.id, imd.res_id
              FROM repair_order ro
              JOIN ir_model_data imd
                ON imd.module = 'mc_rov'
               AND imd.name = %s
               AND imd.model = 'mc.rov.tipo.intervencion'
             WHERE ro.tipo_intervencion = %s
            ON CONFLICT DO NOTHING
        """,
            (xml_name, valor_antiguo),
        )
        migradas += cr.rowcount

    cr.execute("ALTER TABLE repair_order DROP COLUMN tipo_intervencion")

    _logger.info(
        "mc_rov: %s órdenes de reparación migradas de tipo_intervencion a "
        "tipo_intervencion_ids.",
        migradas,
    )
