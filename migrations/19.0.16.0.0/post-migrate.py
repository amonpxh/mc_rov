"""19.0.16.0.0 — la prueba de banco, y las columnas de terreno salen del número de serie.

Tres renombres y un retiro:

- **`tipo = fabricacion` pasa a `banco`.** El valor viejo era genérico y nunca tuvo
  justificación escrita, y además había dejado de describir una sola cosa: lo que pasa
  mientras se arma son puntos de calidad, y lo que pasa después es esta prueba. Se llama
  `banco` y no `rendimiento` porque tiene que contrastar con `terreno` en el mismo eje —dónde
  se prueba—, o el desplegable deja abierta la pregunta «¿y la de terreno no mide
  rendimiento?».
- **`aplica_fabricacion` pasa a `aplica_banco`** en el catálogo de chequeos, por lo mismo.
- **`observacion` pasa a `detalle`** en la línea de inspección de sellos. Había tres nombres
  para la misma idea —`detalle` en la línea de chequeo, `detalle` en la de hallazgo, y
  `observacion` en la de sellos—; como esta versión lleva migración de todos modos, unificarlo
  salió gratis.
- **Se retiran las columnas de prueba en terreno del lote.** Eran el resultado de un evento
  guardado como si fuera ficha técnica, así que correr la prueba dos veces pisaba la anterior
  en silencio. Ahora son una revisión de tipo `terreno`, que sí lleva historial.

El § 8 del diseño verificó **cero filas afectadas** por el retiro. Aun así se cuentan y se
vuelcan al log antes de borrar: lo que valía el 2026-08-18 puede no valer el día que esto
corra, y la lección de `19.0.15.0.0` es que el aviso de lo que se pierde tiene que llegar
**antes** de que las filas se vayan, no después.

Los renombres usan `UPDATE` + `DROP COLUMN` y no `RENAME COLUMN` porque el ORM crea las
columnas nuevas **antes** de ejecutar este script, así que el destino ya existe.
"""

import logging

_logger = logging.getLogger(__name__)

# Las columnas de prueba en terreno que vivían en `stock.lot`, y qué significa «vacía» en
# cada una.
#
# **En las numéricas el cero es indistinguible de no haber llenado nada**, porque Odoo guarda
# 0 y no NULL en un Integer o un Float que nadie tocó. Es el mismo problema que la ficha
# técnica ya tiene identificado y cubierto con tests. Preguntar solo `IS NOT NULL` hace que
# este script avise de datos que no existen — y **un aviso que grita en falso es peor que no
# tenerlo**, porque la próxima vez que haya datos de verdad nadie lo va a mirar. Se descubrió
# ensayando en staging contra una copia de producción, que es exactamente para lo que está.
COLUMNAS_TERRENO = {
    "mc_fecha_prueba": "{c} IS NOT NULL",
    "mc_lugar": "{c} IS NOT NULL AND {c} <> ''",
    "mc_profundidad": "{c} IS NOT NULL AND {c} <> 0",
    "mc_velocidad_corriente": "{c} IS NOT NULL AND {c} <> 0",
    "mc_alimentacion": "{c} IS NOT NULL AND {c} <> ''",
    "mc_tiempo_prueba_terreno": "{c} IS NOT NULL AND {c} <> 0",
    "mc_temperatura_interior_terreno": "{c} IS NOT NULL AND {c} <> 0",
    "mc_temperatura_exterior_terreno": "{c} IS NOT NULL AND {c} <> 0",
    "mc_observacion": "{c} IS NOT NULL AND {c} <> ''",
}


def _existe_columna(cr, tabla, columna):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
        (tabla, columna),
    )
    return bool(cr.fetchone())


def _renombrar_columna(cr, tabla, viejo, nuevo):
    """Copia el contenido a la columna nueva y borra la vieja.

    Nada que hacer si la vieja ya no está: el script es idempotente porque una migración
    puede reejecutarse al reinstalar el módulo sobre una base ya migrada.
    """
    if not _existe_columna(cr, tabla, viejo):
        _logger.info("mc_rov 19.0.16.0.0: %s.%s ya no existe, nada que renombrar", tabla, viejo)
        return
    if not _existe_columna(cr, tabla, nuevo):
        _logger.error(
            "mc_rov 19.0.16.0.0: %s.%s no existe todavía; el ORM debería haberla creado "
            "antes de este script. Se aborta el renombre para no perder %s.",
            tabla,
            nuevo,
            viejo,
        )
        return

    cr.execute(f"UPDATE {tabla} SET {nuevo} = {viejo} WHERE {viejo} IS NOT NULL")
    _logger.info(
        "mc_rov 19.0.16.0.0: %s fila(s) de %s.%s copiadas a %s",
        cr.rowcount,
        tabla,
        viejo,
        nuevo,
    )
    cr.execute(f"ALTER TABLE {tabla} DROP COLUMN {viejo}")


def _tipo_fabricacion_pasa_a_banco(cr):
    cr.execute("UPDATE mc_rov_revision SET tipo = 'banco' WHERE tipo = 'fabricacion'")
    _logger.info("mc_rov 19.0.16.0.0: %s revisión(es) pasaron de fabricación a banco", cr.rowcount)


def _avisar_de_las_pruebas_de_terreno(cr):
    """Vuelca al log los lotes que tuvieran datos de prueba en terreno, antes de borrarlos.

    El diseño verificó que no hay ninguno. Si aparece alguno, es que alguien alcanzó a usar
    esas columnas entre la verificación y el despliegue — y entonces este log es la única
    copia que va a quedar.
    """
    presentes = [c for c in COLUMNAS_TERRENO if _existe_columna(cr, "stock_lot", c)]
    if not presentes:
        _logger.info("mc_rov 19.0.16.0.0: las columnas de prueba en terreno ya no están")
        return []

    condicion = " OR ".join(COLUMNAS_TERRENO[c].format(c=c) for c in presentes)
    columnas = ", ".join(presentes)
    cr.execute(f"SELECT id, name, {columnas} FROM stock_lot WHERE {condicion} ORDER BY id")
    filas = cr.fetchall()

    if not filas:
        _logger.info(
            "mc_rov 19.0.16.0.0: ningún número de serie tenía datos de prueba en terreno, "
            "como anticipaba el § 8 del diseño. Los ceros de las columnas numéricas no "
            "cuentan: en Odoo un Float sin llenar se guarda como 0 y no como NULL."
        )
        return presentes

    _logger.warning(
        "mc_rov 19.0.16.0.0: %s número(s) de serie tienen datos de prueba en terreno y esas "
        "columnas se retiran. Se listan a continuación para que el dato no desaparezca sin "
        "registro; hay que volver a cargarlos como revisión de tipo terreno.",
        len(filas),
    )
    _logger.warning("mc_rov 19.0.16.0.0: columnas -> id, name, %s", columnas)
    for fila in filas:
        _logger.warning("mc_rov 19.0.16.0.0: prueba en terreno descartada -> %s", fila)
    return presentes


def migrate(cr, version):
    """Sin `version` es una instalación limpia y no hay nada que migrar."""
    if not version:
        return

    _tipo_fabricacion_pasa_a_banco(cr)
    _renombrar_columna(cr, "mc_rov_chequeo", "aplica_fabricacion", "aplica_banco")
    _renombrar_columna(cr, "mc_rov_revision_inspeccion", "observacion", "detalle")

    for columna in _avisar_de_las_pruebas_de_terreno(cr):
        cr.execute(f"ALTER TABLE stock_lot DROP COLUMN {columna}")
    _logger.info("mc_rov 19.0.16.0.0: columnas de prueba en terreno retiradas del número de serie")
