import logging

from psycopg2 import sql

_logger = logging.getLogger(__name__)

# El valor que se retiró de las Selection de la ficha técnica.
VALOR_RETIRADO = "Desconocido"

# Las ocho columnas que lo ofrecían.
COLUMNAS = (
    "mc_chasis",
    "mc_modelo_motores",
    "mc_posicion_motores",
    "mc_sensor_presion",
    "mc_tarjeta_comunicacion_rov",
    "mc_tarjeta_comunicacion_consola",
    "mc_controlador_vuelo",
    "mc_software_superficie",
)


def migrate(cr, version):
    """Vacía los «Desconocido» que quedaron de la versión anterior.

    En 19.0.6.0.0 las Selection de la ficha técnica ofrecían «Desconocido» para poder
    guardar equipos anteriores a Odoo sin inventar datos. Se retiró: se prefiere obligar a
    investigar las especificaciones del equipo antes que aceptar un no-dato.

    Sin este script, una serie que alcanzó a guardarse con ese valor conservaría en la base
    una opción que la Selection ya no ofrece. Odoo no falla con eso —muestra el campo en
    blanco— pero el valor sigue ahí, invisible, y reaparecería en cualquier exportación o
    consulta del pipeline. Vaciarlo lo vuelve lo que es: un campo sin llenar, que es
    exactamente lo que el filtro «Ficha incompleta» debe encontrar.

    En una base donde nadie alcanzó a usarlo, no toca nada.
    """
    total = 0
    for columna in COLUMNAS:
        cr.execute(
            sql.SQL("UPDATE stock_lot SET {col} = NULL WHERE {col} = %s").format(
                col=sql.Identifier(columna)
            ),
            (VALOR_RETIRADO,),
        )
        if cr.rowcount:
            _logger.info(
                "mc_rov 19.0.7.0.0: %s filas de stock_lot.%s tenían «%s» y quedaron vacías.",
                cr.rowcount,
                columna,
                VALOR_RETIRADO,
            )
            total += cr.rowcount

    _logger.info(
        "mc_rov 19.0.7.0.0: %s valores «%s» retirados de la ficha técnica.",
        total,
        VALOR_RETIRADO,
    )
