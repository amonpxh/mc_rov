def migrate(cr, version):
    """Copia datos desde columnas antiguas hacia las mc_* ya creadas por el ORM, luego elimina las antiguas.

    El ORM crea las columnas mc_* vacías antes de ejecutar este script, por lo que no se puede
    usar RENAME (la columna destino ya existe). En cambio se copian los datos y se elimina la vieja.
    """
    renames = [
        ('estado_comercial', 'mc_estado_comercial'),
        ('estado_operativo', 'mc_estado_operativo'),
        ('chasis', 'mc_chasis'),
        ('modelo_motores', 'mc_modelo_motores'),
        ('n_motores', 'mc_n_motores'),
        ('posicion_motores', 'mc_posicion_motores'),
        ('peso_consola', 'mc_peso_consola'),
        ('peso_rov', 'mc_peso_rov'),
        ('sensor_presion', 'mc_sensor_presion'),
        ('tarjeta_comunicacion_rov', 'mc_tarjeta_comunicacion_rov'),
        ('tarjeta_comunicacion_consola', 'mc_tarjeta_comunicacion_consola'),
        ('version_qground', 'mc_version_qground'),
        ('controlador_vuelo', 'mc_controlador_vuelo'),
        ('version_px4', 'mc_version_px4'),
        ('version_navigator', 'mc_version_navigator'),
        ('version_ardusub', 'mc_version_ardusub'),
        ('salida_brazo', 'mc_salida_brazo'),
        ('brazo', 'mc_brazo'),
        ('cantidad_luces', 'mc_cantidad_luces'),
        ('dispositivos_extra', 'mc_dispositivos_extra'),
        ('n_serie_umbilical', 'mc_n_serie_umbilical'),
        ('longitud', 'mc_longitud'),
        ('diametro', 'mc_diametro'),
        ('peso_umbilical', 'mc_peso_umbilical'),
        ('modelo_fuente', 'mc_modelo_fuente'),
        ('fuente_energia', 'mc_fuente_energia'),
        ('tension_salida', 'mc_tension_salida'),
        ('consumo_corriente', 'mc_consumo_corriente'),
        ('en_reposo', 'mc_en_reposo'),
        ('esfuerzo', 'mc_esfuerzo'),
        ('limitacion_pilot_gain', 'mc_limitacion_pilot_gain'),
        ('ganancia_luz', 'mc_ganancia_luz'),
        ('tiempo_prueba_lab', 'mc_tiempo_prueba_lab'),
        ('prueba_leak', 'mc_prueba_leak'),
        ('ancho_banda', 'mc_ancho_banda'),
        ('subida', 'mc_subida'),
        ('bajada', 'mc_bajada'),
        ('temperatura_interior_lab', 'mc_temperatura_interior_lab'),
        ('temperatura_exterior_lab', 'mc_temperatura_exterior_lab'),
        ('fecha_prueba', 'mc_fecha_prueba'),
        ('lugar', 'mc_lugar'),
        ('profundidad', 'mc_profundidad'),
        ('velocidad_corriente', 'mc_velocidad_corriente'),
        ('alimentacion', 'mc_alimentacion'),
        ('tiempo_prueba_terreno', 'mc_tiempo_prueba_terreno'),
        ('temperatura_interior_terreno', 'mc_temperatura_interior_terreno'),
        ('temperatura_exterior_terreno', 'mc_temperatura_exterior_terreno'),
        ('observacion', 'mc_observacion'),
    ]
    for old, new in renames:
        cr.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'stock_lot' AND column_name = %s
        """, (old,))
        if cr.fetchone():
            cr.execute(f'UPDATE stock_lot SET "{new}" = "{old}"')
            cr.execute(f'ALTER TABLE stock_lot DROP COLUMN "{old}"')
