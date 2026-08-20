"""19.0.18.0.0 — la prueba de banco se llama prueba de rendimiento.

Tercer y último nombre para este tipo de revisión, y el que tiene la razón más sólida de los
tres: **es como lo llaman los técnicos.**

- `fabricacion` se retiró en `19.0.16.0.0` por ser genérico y no tener justificación escrita.
- `banco` lo reemplazó porque contrasta con `terreno` en el mismo eje —dónde se prueba— y
  `rendimiento` no. Ese argumento era de taxonomía y sigue siendo cierto.
- **Pierde igual**, porque el vocabulario real le gana a la taxonomía. Preguntado el taller,
  dicen *«la de rendimiento»*, y además es la prueba más exigente de las tres, que es lo que
  la palabra transmite. Es el mismo criterio con que la pestaña del número de serie pasó de
  «Revisiones» a «Pruebas»: la etiqueta es lo único que el usuario lee.

Vuelve al nombre que el diseño traía en su § 4.2, y **lo que se gana no es volver atrás sino
que ahora tiene la razón escrita** — que era justamente lo que le faltaba, y por lo que se
retiró `fabricacion`.

Cambiar de nombre tres veces en un día cuesta tres migraciones, y es barato **solo porque el
sistema todavía no se usa con datos reales**. Después de la carga, cada una de éstas habría
sido cara.
"""

import logging

_logger = logging.getLogger(__name__)


def _existe_columna(cr, tabla, columna):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
        (tabla, columna),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    """Sin `version` es una instalación limpia y no hay nada que migrar."""
    if not version:
        return

    cr.execute("UPDATE mc_rov_revision SET tipo = 'rendimiento' WHERE tipo = 'banco'")
    _logger.info("mc_rov 19.0.18.0.0: %s revisión(es) pasaron de banco a rendimiento", cr.rowcount)

    # UPDATE + DROP y no RENAME: el ORM crea la columna destino antes de este script.
    if not _existe_columna(cr, "mc_rov_chequeo", "aplica_banco"):
        _logger.info("mc_rov 19.0.18.0.0: aplica_banco ya no existe, nada que renombrar")
        return
    if not _existe_columna(cr, "mc_rov_chequeo", "aplica_rendimiento"):
        _logger.error(
            "mc_rov 19.0.18.0.0: aplica_rendimiento no existe todavía; el ORM debería haberla "
            "creado antes de este script. Se aborta para no perder aplica_banco."
        )
        return

    cr.execute(
        "UPDATE mc_rov_chequeo SET aplica_rendimiento = aplica_banco WHERE aplica_banco IS NOT NULL"
    )
    _logger.info(
        "mc_rov 19.0.18.0.0: %s chequeo(s) copiados de aplica_banco a aplica_rendimiento",
        cr.rowcount,
    )
    cr.execute("ALTER TABLE mc_rov_chequeo DROP COLUMN aplica_banco")
