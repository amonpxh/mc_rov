import logging

_logger = logging.getLogger(__name__)

# Columnas que este upgrade retira, una vez volcado su contenido.
COLUMNAS_RETIRADAS = ("mc_version_px4", "mc_version_navigator", "mc_version_qground")


def _existe_columna(cr, columna):
    """Permite reintentar el upgrade sin que falle por columnas ya retiradas."""
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'stock_lot' AND column_name = %s
    """,
        (columna,),
    )
    return bool(cr.fetchone())


def _fusionar_version_controlador(cr):
    """Vuelca mc_version_px4 y mc_version_navigator en un solo mc_version_controlador.

    Las dos columnas nunca convivieron: un equipo lleva Pixhawk o Navigator, así que en
    cada fila una de las dos estaba siempre vacía. Se conserva la que corresponde al
    controlador elegido, y si esa viniera vacía se usa la otra antes que perder el dato:
    una versión guardada en la columna equivocada sigue siendo la versión del equipo.
    """
    if not (_existe_columna(cr, "mc_version_px4") and _existe_columna(cr, "mc_version_navigator")):
        _logger.info("mc_rov 19.0.6.0.0: las columnas de versión ya fueron fusionadas.")
        return

    # Filas con las dos llenas: son inconsistencias previas y conviene que queden en el log
    # del deploy, porque el volcado se queda con una sola.
    cr.execute(
        """
        SELECT COUNT(*) FROM stock_lot
         WHERE NULLIF(TRIM(mc_version_px4), '') IS NOT NULL
           AND NULLIF(TRIM(mc_version_navigator), '') IS NOT NULL
    """
    )
    ambiguas = cr.fetchone()[0]

    cr.execute(
        """
        UPDATE stock_lot
           SET mc_version_controlador = CASE
                   WHEN mc_controlador_vuelo = 'Pixhawk' THEN COALESCE(
                       NULLIF(TRIM(mc_version_px4), ''), NULLIF(TRIM(mc_version_navigator), ''))
                   WHEN mc_controlador_vuelo = 'Navigator' THEN COALESCE(
                       NULLIF(TRIM(mc_version_navigator), ''), NULLIF(TRIM(mc_version_px4), ''))
                   ELSE COALESCE(
                       NULLIF(TRIM(mc_version_px4), ''), NULLIF(TRIM(mc_version_navigator), ''))
               END
         WHERE mc_version_controlador IS NULL
    """
    )

    _logger.info(
        "mc_rov 19.0.6.0.0: mc_version_controlador poblado en %s filas. "
        "%s traían las dos versiones llenas y se resolvieron por el controlador elegido.",
        cr.rowcount,
        ambiguas,
    )


def _mover_software_superficie(cr):
    """Convierte mc_version_qground en el par selector + versión.

    El campo viejo asumía que QGroundControl era el único software de superficie. Ya no lo
    es —hay Crabby y ROVControl— pero todo lo que se guardó ahí sí era una versión de
    QGround, porque no había dónde poner otra cosa. Por eso el selector se siembra con
    QGroundControl solo en las filas que traían valor: sembrarlo en las vacías inventaría
    un dato que nadie afirmó.
    """
    if not _existe_columna(cr, "mc_version_qground"):
        _logger.info("mc_rov 19.0.6.0.0: el software de superficie ya fue migrado.")
        return

    cr.execute(
        """
        UPDATE stock_lot
           SET mc_version_software = NULLIF(TRIM(mc_version_qground), ''),
               mc_software_superficie = 'QGroundControl'
         WHERE mc_version_software IS NULL
           AND NULLIF(TRIM(mc_version_qground), '') IS NOT NULL
    """
    )

    _logger.info(
        "mc_rov 19.0.6.0.0: %s fichas pasaron a QGroundControl con su versión.", cr.rowcount
    )


def _retirar_columnas_viejas(cr):
    """Elimina las columnas ya volcadas.

    Va al final y en su propio paso: si algo falla en los volcados anteriores, el upgrade
    se corta con los datos todavía en su sitio.
    """
    for columna in COLUMNAS_RETIRADAS:
        if _existe_columna(cr, columna):
            cr.execute(f"ALTER TABLE stock_lot DROP COLUMN {columna}")
            _logger.info("mc_rov 19.0.6.0.0: columna stock_lot.%s eliminada.", columna)


def migrate(cr, version):
    """Reemplaza tres columnas de versión por dos pares selector + versión.

    Antes había una columna por producto: mc_version_qground, mc_version_px4,
    mc_version_navigator. Eso obliga a desplegar código cada vez que cambia el panorama, y
    el panorama ya está cambiando — ROVControl es temporal y lo reemplaza Crabby, y
    Navigator también se va a reemplazar. Ahora el producto se elige de una lista y la
    versión es una sola columna.

    El orden importa: primero se vuelca todo, después se eliminan las columnas. Nunca al
    revés, y nunca en el mismo paso.

    mc_ficha_completa no se toca acá: es una columna nueva, y a las columnas nuevas el ORM
    las calcula sola al final de la carga del módulo, o sea después de este script.
    """
    _fusionar_version_controlador(cr)
    _mover_software_superficie(cr)
    _retirar_columnas_viejas(cr)
