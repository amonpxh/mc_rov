"""19.0.14.0.0 — la temperatura baja de la revisión a la corrida.

`temperatura_interior` y `temperatura_exterior` vivían en `mc.rov.revision`, clasificadas
como «mediciones que no dependen del cable». Las dos mitades de esa frase eran falsas:

1. **Se mide una por corrida, no una por sesión.** Con dos umbilicales son dos lecturas, y
   guardarlas en la cabecera obligaba a elegir una o a promediarlas — las dos cosas pierden
   justamente la comparación que hace útil correr con el umbilical de prueba.
2. **Sí dependen del cable.** Un umbilical largo cae tensión y calienta, así que la
   temperatura es de las mediciones que más dependen de él.

El traspaso de datos se resolvió antes de escribir esto: la auditoría en `odoo_prod` no
devolvió **ninguna** revisión con temperatura registrada, así que no hay nada que repartir
entre corridas —que es la parte que no tendría solución honesta, porque una lectura de sesión
no se puede desdoblar en dos de corrida sin inventar la segunda—.

Aun así el script mira antes de borrar, y **si encuentra datos no borra nada**: prefiere dejar
dos columnas huérfanas en la tabla, que son inertes, antes que perder mediciones sin aviso.
"""

import logging

_logger = logging.getLogger(__name__)


def _existe_columna(cr, tabla, columna):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
         WHERE table_name = %s AND column_name = %s
        """,
        (tabla, columna),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    """Sin `version` es una instalación limpia y no hay nada que migrar."""
    if not version:
        return

    if not _existe_columna(cr, "mc_rov_revision", "temperatura_interior"):
        _logger.info("mc_rov 19.0.14.0.0: la temperatura ya no está en la revisión")
        return

    cr.execute(
        """
        SELECT count(*) FROM mc_rov_revision
         WHERE COALESCE(temperatura_interior, 0) <> 0
            OR COALESCE(temperatura_exterior, 0) <> 0
        """
    )
    con_datos = cr.fetchone()[0]

    if con_datos:
        # No se borra. Una lectura de sesión no se puede repartir entre las corridas sin
        # inventar, y elegir una corrida al azar sería peor: el dato quedaría atribuido a un
        # cable que puede no ser el que se midió.
        _logger.warning(
            "mc_rov 19.0.14.0.0: %s revisión(es) tienen temperatura registrada. Las columnas "
            "viejas NO se eliminan para no perderlas; hay que trasladarlas a mano a la "
            "corrida que corresponda y después borrarlas.",
            con_datos,
        )
        return

    cr.execute(
        """
        ALTER TABLE mc_rov_revision
            DROP COLUMN IF EXISTS temperatura_interior,
            DROP COLUMN IF EXISTS temperatura_exterior
        """
    )
    _logger.info(
        "mc_rov 19.0.14.0.0: temperaturas retiradas de la revisión (sin datos que trasladar). "
        "El ORM las creará en mc_rov_revision_corrida."
    )
