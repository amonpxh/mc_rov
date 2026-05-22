def migrate(cr, version):
    """Migra linea_falla.accion (Selection varchar) a accion_id (Many2one int).

    El ORM ya creó la columna accion_id y los datos XML ya cargaron los registros
    mc.rov.accion antes de que este script ejecute (post-migrate corre al final).
    Solo actúa si la columna antigua 'accion' existe (no aplica en instalaciones frescas).
    """
    cr.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'mc_rov_linea_falla' AND column_name = 'accion'
    """
    )
    if not cr.fetchone():
        return

    # Los XML IDs definidos en mc_rov_data.xml para cada valor de la selección antigua
    mapping = {
        "cambio_completo": "accion_cambio_completo",
        "cambio_componente": "accion_cambio_componente",
        "reparacion": "accion_reparacion",
        "mantencion_preventiva": "accion_mantencion_preventiva",
        "limpieza": "accion_limpieza",
        "calibracion": "accion_calibracion",
        "configuracion": "accion_configuracion",
        "soldadura": "accion_soldadura",
        "sin_solucion": "accion_sin_solucion",
        "derivado": "accion_derivado",
    }
    for old_val, xml_name in mapping.items():
        cr.execute(
            """
            UPDATE mc_rov_linea_falla lf
            SET accion_id = imd.res_id
            FROM ir_model_data imd
            WHERE imd.module = 'mc_rov'
              AND imd.name = %s
              AND lf.accion = %s
        """,
            (xml_name, old_val),
        )

    cr.execute("ALTER TABLE mc_rov_linea_falla DROP COLUMN accion")
