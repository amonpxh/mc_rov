"""19.0.21.0.0 — tres cálculos cambian de regla, así que hay que rehacerlos.

**Odoo no recalcula un campo almacenado cuyo cambio está solo en el código.** La columna ya
existe con datos, así que actualizar el módulo no la toca: los valores viejos se quedan,
calculados con la regla anterior, y el defecto sigue en pantalla como si no se hubiera
arreglado nada. Los tres de esta versión:

- **`resultado`** ahora vale vacío mientras la revisión sea borrador. Sin este script, las
  revisiones en borrador que ya existen conservan su «Aprobado» en la columna de las listas,
  que es exactamente el defecto que se vino a corregir.
- **`software_difiere`** pasa a comparar los cinco campos y no las tres versiones, así que un
  equipo con otro controlador de vuelo tiene que empezar a marcar diferencia.
- **La foto de la ficha** de las revisiones en borrador se pone al día. Ésas son las que se
  crearon antes de que la foto siguiera a la ficha, y hasta que alguien las guarde estarían
  comparando contra lo que la ficha decía el día que se abrieron — o contra nada, si la ficha
  se llenó después.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Sin `version` es una instalación limpia y no hay nada que rehacer."""
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    Revision = env["mc.rov.revision"]

    # Se recalculan a través del ORM y no con UPDATE: la regla nueva vive en Python, y
    # duplicarla en SQL dejaría dos versiones que se pueden desincronizar en el próximo cambio.
    todas = Revision.search([])
    for nombre in ("resultado", "software_difiere"):
        env.add_to_compute(Revision._fields[nombre], todas)
    env.flush_all()

    con_veredicto = Revision.search_count([("resultado", "!=", False)])
    difieren = Revision.search_count([("software_difiere", "=", True)])
    _logger.info(
        "mc_rov 19.0.21.0.0: %s revisión(es) recalculadas — %s con veredicto, "
        "%s con software que no cuadra",
        len(todas),
        con_veredicto,
        difieren,
    )

    borradores = Revision.search([("estado", "=", "borrador")])
    borradores._refrescar_ficha()
    _logger.info(
        "mc_rov 19.0.21.0.0: %s borrador(es) con la foto de la ficha al día",
        len(borradores),
    )
