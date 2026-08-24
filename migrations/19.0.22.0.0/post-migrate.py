"""19.0.22.0.0 — la estanqueidad vuelve a la batería de terreno.

`19.0.20.0.0` la sacó siguiendo la tabla de totales del § 5.3 del diseño de fabricación, que
**se contradice con su propio § 5.2**: ese párrafo dice, con todas sus letras, que *el chequeo
de estanqueidad está en las tres y lo que cambia son las mediciones*. Manda el § 5.2 — en el
muelle no hay máquina de presión, pero el equipo baja igual, y la profundidad alcanzada no es
contexto sino la misma verificación hecha por otro medio.

El reparto queda en **rendimiento 18 · terreno 18 · reparación 24**.

Hace falta un script por lo mismo que en `19.0.20.0.0`: el catálogo de chequeos es `noupdate`
desde entonces, así que Odoo ya no le aplica los valores del XML a los registros que existen.
Y ojo con lo que eso implica acá: **si alguien ya había apagado esta casilla a mano, este
script se la vuelve a encender.** Es aceptable una vez, porque el valor que se está corrigiendo
lo puso el módulo y no una persona, pero queda registrado en el log.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Sin `version` es una instalación limpia: el XML ya trae el reparto correcto."""
    if not version:
        return

    cr.execute(
        "SELECT res_id FROM ir_model_data WHERE module = 'mc_rov' "
        "AND name = 'chequeo_estanqueidad' AND model = 'mc.rov.chequeo'"
    )
    fila = cr.fetchone()
    if not fila:
        _logger.warning(
            "mc_rov 19.0.22.0.0: no existe el chequeo de estanqueidad, se omite. La batería "
            "de terreno se queda como esté."
        )
        return

    cr.execute("SELECT aplica_terreno FROM mc_rov_chequeo WHERE id = %s", (fila[0],))
    antes = cr.fetchone()[0]
    if antes:
        _logger.info("mc_rov 19.0.22.0.0: la estanqueidad ya estaba en terreno, nada que hacer")
        return

    cr.execute("UPDATE mc_rov_chequeo SET aplica_terreno = true WHERE id = %s", (fila[0],))
    _logger.info("mc_rov 19.0.22.0.0: la estanqueidad vuelve a la batería de terreno")

    cr.execute(
        "SELECT count(*) FILTER (WHERE aplica_rendimiento), "
        "count(*) FILTER (WHERE aplica_terreno), "
        "count(*) FILTER (WHERE aplica_reparacion) FROM mc_rov_chequeo"
    )
    _logger.info("mc_rov 19.0.22.0.0: rendimiento %s · terreno %s · reparación %s", *cr.fetchone())
