"""19.0.12.0.0 — recalcular la evidencia de manipulación.

`manipulacion_externa` comparaba el tipo de la revisión contra 'recepcion' y ahora lo
compara contra 'reparacion'. El pre-migrate ya movió los tipos, pero eso no basta: el ORM
solo calcula solo las columnas que acaba de crear, y esta existe desde 19.0.11.0.0 con
datos adentro. Sin este recálculo, las inspecciones que venían de una revisión de entrega
—que antes nunca encendían la marca— quedarían diciendo que no hubo manipulación sin que
nadie la haya evaluado con la regla nueva.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    Inspeccion = env["mc.rov.revision.inspeccion"]

    lineas = Inspeccion.search([])
    if not lineas:
        _logger.info("mc_rov: no hay inspecciones de sellos, nada que recalcular")
        return

    env.add_to_compute(Inspeccion._fields["manipulacion_externa"], lineas)
    env.flush_all()
    _logger.info("mc_rov: %s inspecciones de sellos recalculadas", len(lineas))
