"""19.0.15.2.1 — la línea de chequeo hereda la secuencia del catálogo.

`mc.rov.revision.chequeo.sequence` era un `Integer(default=10)`: **el mismo valor en todas
las líneas**, así que `_order = "revision_id, sequence, id"` caía a `id` y la ficha se mostraba
en orden de creación. Pasa a ser `related` almacenado de `chequeo_id.sequence`.

**Por qué hace falta un script.** Odoo no recalcula un almacenado existente solo porque su
definición cambió: la columna ya está, con 10 en todas las filas, y sin este `UPDATE` las
revisiones que ya existen seguirían mostrando el orden viejo para siempre. Las nuevas saldrían
bien, que es el peor de los dos mundos — el defecto se vuelve invisible justo donde se prueba.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Sin `version` es una instalación limpia: no hay líneas que reordenar."""
    if not version:
        return

    cr.execute(
        """
        UPDATE mc_rov_revision_chequeo l
           SET sequence = c.sequence
          FROM mc_rov_chequeo c
         WHERE c.id = l.chequeo_id
           AND l.sequence IS DISTINCT FROM c.sequence
        """
    )
    _logger.info(
        "mc_rov 19.0.15.2.1: %s línea(s) de chequeo recuperaron la secuencia del catálogo",
        cr.rowcount,
    )
