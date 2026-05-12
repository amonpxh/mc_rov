def migrate(cr, version):
    """Copia datos desde campos x_studio_* de Studio hacia los campos propios del módulo."""
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'stock_lot' AND column_name = 'x_studio_estado_comercial'
    """)
    if not cr.fetchone():
        return  # instalación nueva sin datos de Studio, nada que migrar

    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'stock_lot' AND column_name = 'estado_comercial'
    """)
    if not cr.fetchone():
        return  # columnas intermedias (sin mc_) no existen: el ORM ya usa mc_* directamente

    cr.execute("""
        UPDATE stock_lot SET
            estado_comercial          = x_studio_estado_comercial,
            estado_operativo          = x_studio_estado_operativo,
            chasis                    = x_studio_chasis_1,
            modelo_motores            = x_studio_modelo_motores,
            n_motores                 = COALESCE(x_studio_n_motores, 0),
            posicion_motores          = x_studio_posicion_motores,
            peso_consola              = COALESCE(x_studio_peso_consola_1, 0),
            peso_rov                  = COALESCE(x_studio_peso_rov_1, 0),
            sensor_presion            = x_studio_sensor_de_presion,
            tarjeta_comunicacion_rov  = x_studio_tarjeta_de_comunicacion_rov,
            tarjeta_comunicacion_consola = x_studio_tarjeta_de_comunicacion_consola,
            version_qground           = x_studio_version_qground,
            controlador_vuelo         = x_studio_controlador_de_vuelo,
            version_px4               = x_studio_version_px4_1,
            version_navigator         = x_studio_version_navigator,
            version_ardusub           = x_studio_version_ardusub,
            salida_brazo              = COALESCE(x_studio_salida_de_brazo, false),
            brazo                     = x_studio_brazo,
            cantidad_luces            = COALESCE(x_studio_cantidad_de_luces, 0),
            dispositivos_extra        = x_studio_dispositivos_extra,
            n_serie_umbilical         = x_studio_n_serie_de_umbilical,
            longitud                  = COALESCE(x_studio_longitud_1, 0),
            diametro                  = COALESCE(x_studio_diametro_1, 0),
            peso_umbilical            = COALESCE(x_studio_peso_umbilical_1, 0),
            modelo_fuente             = x_studio_modelo_de_fuente,
            fuente_energia            = x_studio_fuente_de_energia,
            tension_salida            = COALESCE(x_studio_tension_de_salida_1, 0),
            consumo_corriente         = x_studio_consumo_corriente,
            en_reposo                 = COALESCE(x_studio_en_reposo_1, 0),
            esfuerzo                  = COALESCE(x_studio_esfuerzo_1, 0),
            limitacion_pilot_gain     = COALESCE(x_studio_limitacion_pilot_gain, 0),
            ganancia_luz              = COALESCE(x_studio_ganancia_luz_1, 0),
            tiempo_prueba_lab         = COALESCE(x_studio_tiempo_de_prueba_2, 0),
            prueba_leak               = COALESCE(x_studio_prueba_de_leak_3, false),
            ancho_banda               = x_studio_ancho_de_banda_puede_variar_5,
            subida                    = COALESCE(x_studio_subida_1, 0),
            bajada                    = COALESCE(x_studio_bajada_1, 0),
            temperatura_interior_lab  = COALESCE(x_studio_temperatura_interior_2, 0),
            temperatura_exterior_lab  = COALESCE(x_studio_temperatura_exterior_2, 0),
            fecha_prueba              = x_studio_fecha_1,
            lugar                     = x_studio_lugar,
            profundidad               = COALESCE(x_studio_profundidad_1, 0),
            velocidad_corriente       = COALESCE(x_studio_velocidad_de_la_corriente_1, 0),
            alimentacion              = x_studio_alimentacion_1,
            tiempo_prueba_terreno     = COALESCE(x_studio_tiempo_de_prueba_3, 0),
            temperatura_interior_terreno = COALESCE(x_studio_temperatura_interior_3, 0),
            temperatura_exterior_terreno = COALESCE(x_studio_temperatura_exterior_3, 0),
            observacion               = x_studio_observacion
        WHERE es_un_rov = true
    """)
