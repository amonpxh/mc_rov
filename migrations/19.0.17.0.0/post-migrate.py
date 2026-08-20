"""19.0.17.0.0 — las columnas de prueba de banco salen del número de serie.

Cierra lo que `19.0.16.0.0` empezó con las de terreno. **Trece columnas de `stock.lot`** que
guardaban el resultado de la prueba de banco: modelo de fuente, fuente de energía, tensión,
consumo, en reposo, esfuerzo, tiempo de prueba, prueba de leak, ancho de banda, subida,
bajada y las dos temperaturas de laboratorio.

Tenían dos defectos a la vez. Eran el resultado de un **evento** guardado como si fuera ficha
técnica, así que correr la prueba dos veces pisaba la anterior en silencio. Y desde
`19.0.15.0.0` **estaban duplicadas**: la revisión recogía las mismas mediciones, de modo que
el mismo dato se tecleaba dos veces sin ninguna señal de que sobraba.

**Dos de las quince sobreviven y no se tocan:** `mc_limitacion_pilot_gain` y
`mc_ganancia_luz`. No son medición, son configuración del equipo — o sea ficha. La prueba de
banco y la de terreno las miden; la revisión de reparación las muestra desde la ficha para
ver si cambiaron (§ 5.4).

Y se retira la palabra «esfuerzo», que significaba tres cosas a la vez (§ 5.5):
`esfuerzo_duracion` y `esfuerzo_resultado` pasan a `funcionamiento_continuo_*`, porque la
corrida de hora y media en el bin no es el consumo bajo carga de la ficha ni el conjunto.

**Lo mismo que la vez pasada: se cuenta y se vuelca al log antes de borrar, y el vacío se
juzga por tipo.** Un `Integer` o un `Float` que nadie llenó vale 0 y no NULL, así que
preguntar solo `IS NOT NULL` haría que este script avisara de datos que no existen — y un
aviso que grita en falso es peor que no tenerlo.
"""

import logging

_logger = logging.getLogger(__name__)

# Las columnas de prueba de banco que vivían en `stock.lot`, y qué significa «vacía» en cada
# una. Los `Char` y `Boolean` se juzgan distinto que los numéricos por la misma razón que en
# 19.0.16.0.0: el cero no es un dato, es la falta de uno.
COLUMNAS_BANCO = {
    "mc_modelo_fuente": "{c} IS NOT NULL AND {c} <> ''",
    "mc_fuente_energia": "{c} IS NOT NULL AND {c} <> ''",
    "mc_tension_salida": "{c} IS NOT NULL AND {c} <> 0",
    "mc_consumo_corriente": "{c} IS NOT NULL AND {c} <> ''",
    "mc_en_reposo": "{c} IS NOT NULL AND {c} <> 0",
    "mc_esfuerzo": "{c} IS NOT NULL AND {c} <> 0",
    "mc_tiempo_prueba_lab": "{c} IS NOT NULL AND {c} <> 0",
    "mc_prueba_leak": "{c} IS TRUE",
    "mc_ancho_banda": "{c} IS NOT NULL AND {c} <> ''",
    "mc_subida": "{c} IS NOT NULL AND {c} <> 0",
    "mc_bajada": "{c} IS NOT NULL AND {c} <> 0",
    "mc_temperatura_interior_lab": "{c} IS NOT NULL AND {c} <> 0",
    "mc_temperatura_exterior_lab": "{c} IS NOT NULL AND {c} <> 0",
}

# Los renombres de la revisión. El ORM ya creó la columna destino cuando esto corre, así que
# es UPDATE + DROP y nunca RENAME.
RENOMBRES = [
    ("esfuerzo_duracion", "funcionamiento_continuo_duracion"),
    ("esfuerzo_resultado", "funcionamiento_continuo_resultado"),
]


def _existe_columna(cr, tabla, columna):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
        (tabla, columna),
    )
    return bool(cr.fetchone())


def _renombrar_columna(cr, tabla, viejo, nuevo):
    """Copia el contenido a la columna nueva y borra la vieja. Idempotente."""
    if not _existe_columna(cr, tabla, viejo):
        _logger.info("mc_rov 19.0.17.0.0: %s.%s ya no existe, nada que renombrar", tabla, viejo)
        return
    if not _existe_columna(cr, tabla, nuevo):
        _logger.error(
            "mc_rov 19.0.17.0.0: %s.%s no existe todavía; el ORM debería haberla creado antes "
            "de este script. Se aborta el renombre para no perder %s.",
            tabla,
            nuevo,
            viejo,
        )
        return

    cr.execute(f"UPDATE {tabla} SET {nuevo} = {viejo} WHERE {viejo} IS NOT NULL")
    _logger.info(
        "mc_rov 19.0.17.0.0: %s fila(s) de %s.%s copiadas a %s", cr.rowcount, tabla, viejo, nuevo
    )
    cr.execute(f"ALTER TABLE {tabla} DROP COLUMN {viejo}")


def _avisar_de_las_pruebas_de_banco(cr):
    """Vuelca al log los equipos con datos de prueba de banco, antes de borrarlos.

    A diferencia de las columnas de terreno, **aquí sí puede haber mediciones reales**: son
    las que el taller venía llenando. Si aparecen, este log es la única copia que va a quedar
    y hay que volver a cargarlas como prueba de banco.
    """
    presentes = [c for c in COLUMNAS_BANCO if _existe_columna(cr, "stock_lot", c)]
    if not presentes:
        _logger.info("mc_rov 19.0.17.0.0: las columnas de prueba de banco ya no están")
        return []

    condicion = " OR ".join(COLUMNAS_BANCO[c].format(c=c) for c in presentes)
    columnas = ", ".join(presentes)
    cr.execute(f"SELECT id, name, {columnas} FROM stock_lot WHERE {condicion} ORDER BY id")
    filas = cr.fetchall()

    if not filas:
        _logger.info(
            "mc_rov 19.0.17.0.0: ningún número de serie tenía datos de prueba de banco. Los "
            "ceros de las columnas numéricas no cuentan: en Odoo un Float sin llenar se "
            "guarda como 0 y no como NULL."
        )
        return presentes

    _logger.warning(
        "mc_rov 19.0.17.0.0: %s número(s) de serie tienen datos de prueba de banco y esas "
        "columnas se retiran. Se listan a continuación para que el dato no desaparezca sin "
        "registro; hay que volver a cargarlos como revisión de tipo banco.",
        len(filas),
    )
    _logger.warning("mc_rov 19.0.17.0.0: columnas -> id, name, %s", columnas)
    for fila in filas:
        _logger.warning("mc_rov 19.0.17.0.0: prueba de banco descartada -> %s", fila)
    return presentes


def migrate(cr, version):
    """Sin `version` es una instalación limpia y no hay nada que migrar."""
    if not version:
        return

    for viejo, nuevo in RENOMBRES:
        _renombrar_columna(cr, "mc_rov_revision", viejo, nuevo)

    for columna in _avisar_de_las_pruebas_de_banco(cr):
        cr.execute(f"ALTER TABLE stock_lot DROP COLUMN {columna}")
    _logger.info("mc_rov 19.0.17.0.0: columnas de prueba de banco retiradas del número de serie")
