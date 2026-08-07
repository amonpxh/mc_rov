import logging

_logger = logging.getLogger(__name__)

# Una orden en draft es una cotización: el equipo todavía no entró al taller.
# Debe coincidir con _compute_mc_estado_operativo en models/stock_lot.py.
ESTADOS_CERRADOS = ("draft", "done", "cancel")


def migrate(cr, version):
    """Recalcula mc_estado_operativo, que pasa a derivarse de las órdenes abiertas.

    El ORM no recalcula un campo que pasa a ser computed+store si la columna ya existía
    con datos. Sin esto, los números de serie conservarían el valor que alguien escribió
    a mano y el campo seguiría mintiendo justo en los equipos donde ya estaba desfasado.

    No hay portón como en 19.0.2.0.0: aquí no se pierde información que no sea
    reconstruible. El estado se deriva de las órdenes, que son la fuente real.
    """
    # El orden importa: mantención gana sobre reparación si conviven ambas abiertas.
    cr.execute("UPDATE stock_lot SET mc_estado_operativo = 'Operativo'")
    total = cr.rowcount

    cr.execute(
        """
        UPDATE stock_lot sl SET mc_estado_operativo = 'En reparación'
         WHERE EXISTS (
               SELECT 1 FROM repair_order ro
                WHERE ro.lot_id = sl.id
                  AND ro.state NOT IN %s
         )
    """,
        (ESTADOS_CERRADOS,),
    )
    en_reparacion = cr.rowcount

    cr.execute(
        """
        UPDATE stock_lot sl SET mc_estado_operativo = 'En mantención'
         WHERE EXISTS (
               SELECT 1 FROM repair_order ro
                WHERE ro.lot_id = sl.id
                  AND ro.state NOT IN %s
                  AND ro.tipo_intervencion = 'mantencion_preventiva'
         )
    """,
        (ESTADOS_CERRADOS,),
    )
    en_mantencion = cr.rowcount

    _logger.info(
        "mc_rov: mc_estado_operativo recalculado sobre %s números de serie. "
        "%s en reparación, %s en mantención, el resto operativos.",
        total,
        en_reparacion - en_mantencion,
        en_mantencion,
    )
