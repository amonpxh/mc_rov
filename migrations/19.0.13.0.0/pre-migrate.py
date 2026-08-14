"""19.0.13.0.0 — `causa_raiz` se parte en `origen`.

El campo viejo mezclaba dos preguntas: **qué le pasó físicamente al equipo** y **de quién es
el problema**. La evidencia de que estaba mal planteado son dos de sus seis valores:
`corrosion` es un mecanismo —y existe literalmente como entrada del catálogo de hallazgos— y
`accidente` es una circunstancia. Ninguno de los dos contesta de quién es el problema, que es
lo único que `origen` pregunta.

Va todo en pre-migrate y no en post-migrate por una razón concreta: la columna nueva tiene que
quedar escrita **antes** de que el ORM procese el modelo, para que ninguna fila pase por un
estado en que el valor viejo ya no está y el nuevo todavía no. Como el ORM crea las columnas
nuevas después del pre-migrate, se crea a mano para poder leer la vieja.

Cuatro de las seis claves se reutilizan tal cual —`falla_fabricacion`, `mal_uso`, `desgaste`,
`desconocida`— así que solo dos valores se mueven. El tercer caso, y el que más filas toca, no
es un valor sino su ausencia: `causa_raiz` **nunca fue obligatorio**.
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


def _auditar(cr):
    """Deja en el log cómo estaban las filas antes de tocarlas.

    Es lo que permite comparar después del despliegue contra
    `SELECT origen, count(*) FROM mc_rov_linea_falla GROUP BY origen`. Sin esta foto, un
    número raro más tarde no se puede atribuir ni descartar.
    """
    cr.execute(
        """
        SELECT COALESCE(causa_raiz, '(sin causa)'), count(*)
          FROM mc_rov_linea_falla
         GROUP BY causa_raiz
         ORDER BY 2 DESC
        """
    )
    for valor, cuantas in cr.fetchall():
        _logger.info("mc_rov 19.0.13.0.0: causa_raiz %-20s %s fila(s)", valor, cuantas)


def _migrar_origen(cr):
    cr.execute("ALTER TABLE mc_rov_linea_falla ADD COLUMN IF NOT EXISTS origen varchar")
    cr.execute("UPDATE mc_rov_linea_falla SET origen = causa_raiz")

    # `corrosion` es un mecanismo, no un origen: la corrosión de un equipo puede ser desgaste
    # normal, uso fuera de especificación o una especificación mal puesta, y el dato viejo no
    # dice cuál. Mapearlo a cualquiera de los tres sería inventar. Queda en "No determinado"
    # con el valor anterior anotado en el detalle, que es donde alguien lo puede releer.
    cr.execute(
        """
        UPDATE mc_rov_linea_falla
           SET origen  = 'desconocida',
               detalle = COALESCE(detalle || E'\\n', '')
                         || '[Migración 19.0.13.0.0] Causa anterior: corrosión.'
         WHERE causa_raiz = 'corrosion'
        """
    )
    _logger.info("mc_rov 19.0.13.0.0: %s fila(s) de corrosión pasaron a desconocida", cr.rowcount)

    # `accidente` no pierde nada: la etiqueta nueva es "Uso del cliente (mal uso o
    # accidente)", que lo absorbe explícitamente.
    cr.execute("UPDATE mc_rov_linea_falla SET origen = 'mal_uso' WHERE causa_raiz = 'accidente'")
    _logger.info("mc_rov 19.0.13.0.0: %s fila(s) de accidente pasaron a mal_uso", cr.rowcount)

    # El caso que no es una conversión sino un vacío. `causa_raiz` era opcional, así que hay
    # líneas de trabajo sin ninguna causa registrada. Dejarlas en NULL sería peor que
    # cualquier valor: un NULL acá es indistinguible de un dato que se perdió en la
    # migración, y "No determinado" es exactamente lo que esas filas dicen.
    cr.execute("UPDATE mc_rov_linea_falla SET origen = 'desconocida' WHERE origen IS NULL")
    _logger.info("mc_rov 19.0.13.0.0: %s fila(s) sin causa quedaron en desconocida", cr.rowcount)

    cr.execute("ALTER TABLE mc_rov_linea_falla DROP COLUMN IF EXISTS causa_raiz")


def migrate(cr, version):
    """Sin `version` es una instalación limpia y no hay nada que migrar."""
    if not version:
        return

    if not _existe_columna(cr, "mc_rov_linea_falla", "causa_raiz"):
        _logger.info("mc_rov 19.0.13.0.0: causa_raiz ya no existe, nada que migrar")
        return

    _auditar(cr)
    _migrar_origen(cr)
