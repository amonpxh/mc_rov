import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# Columna de texto apartada por pre-migrate -> modelo del catálogo que la reemplaza.
CONVERSIONES = {
    "mc_software_superficie": "mc.rov.software.superficie",
    "mc_controlador_vuelo": "mc.rov.controlador.vuelo",
}


def _existe_columna(cr, columna):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'stock_lot' AND column_name = %s
    """,
        (columna,),
    )
    return bool(cr.fetchone())


def _traducir(env, campo, modelo):
    """Cambia cada texto guardado por el id del registro de catálogo que le corresponde.

    Empareja por nombre, que es exactamente lo que guardaba el Selection: sus claves eran
    los mismos strings visibles ("QGroundControl", "Navigator"). Un valor que no encuentre
    pareja **se crea en el catálogo** en vez de perderse: puede haber entrado por
    importación o por una versión anterior, y borrarlo sería inventar que el equipo no
    tenía nada.
    """
    cr = env.cr
    columna = f"{campo}_texto"
    if not _existe_columna(cr, columna):
        _logger.info("mc_rov 19.0.9.0.0: %s ya fue traducida.", campo)
        return

    cr.execute(
        f"SELECT DISTINCT {columna} FROM stock_lot WHERE NULLIF(TRIM({columna}), '') IS NOT NULL"
    )
    valores = [fila[0].strip() for fila in cr.fetchall()]

    Catalogo = env[modelo]
    for valor in valores:
        registro = Catalogo.search([("name", "=", valor)], limit=1)
        if not registro:
            registro = Catalogo.create({"name": valor})
            _logger.warning(
                "mc_rov 19.0.9.0.0: «%s» no estaba en %s y se creó para no perder el dato.",
                valor,
                modelo,
            )
        cr.execute(
            f"UPDATE stock_lot SET {campo} = %s WHERE TRIM({columna}) = %s",
            (registro.id, valor),
        )
        _logger.info("mc_rov 19.0.9.0.0: %s filas pasaron a %s = «%s».", cr.rowcount, campo, valor)

    cr.execute(f"ALTER TABLE stock_lot DROP COLUMN {columna}")


def migrate(cr, version):
    """Traduce los textos de los dos campos a referencias de catálogo.

    Corre después de que los archivos de datos sembraron QGroundControl, Crabby, ROVControl,
    Navigator y Pixhawk, así que la búsqueda por nombre encuentra a casi todos. Lo que no,
    se crea.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    for campo, modelo in CONVERSIONES.items():
        _traducir(env, campo, modelo)
