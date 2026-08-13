import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# Columnas de repair.order que este upgrade retira.
COLUMNAS_RETIRADAS = ("item_2", "item_3", "item_4", "item_5")


def _existe_columna(cr, tabla, columna):
    """Permite reintentar el upgrade sin que falle por columnas ya retiradas."""
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
         WHERE table_name = %s AND column_name = %s
    """,
        (tabla, columna),
    )
    return bool(cr.fetchone())


def _bajar_causa_raiz(cr):
    """Copia causa_raiz de cada orden a sus líneas de trabajo antes de retirarla.

    Sube de la orden a la línea porque una visita puede tener tres causas distintas —el
    umbilical cortado por accidente y el motor gastado por uso— y una sola casilla obligaba
    a elegir una y perder las otras. Para un módulo cuyo propósito declarado es el análisis
    de fallas, esa pérdida de resolución era el problema.

    Las órdenes con causa raíz pero sin líneas de trabajo pierden el valor: no hay a qué
    fila copiárselo. Se cuentan y se registran en el log para que quede constancia de
    cuántas fueron.
    """
    if not _existe_columna(cr, "repair_order", "causa_raiz"):
        _logger.info("mc_rov 19.0.8.0.0: causa_raiz ya fue bajada a las líneas.")
        return

    cr.execute(
        """
        SELECT COUNT(*) FROM repair_order ro
         WHERE ro.causa_raiz IS NOT NULL
           AND NOT EXISTS (
                 SELECT 1 FROM mc_rov_linea_falla lf WHERE lf.repair_id = ro.id)
    """
    )
    huerfanas = cr.fetchone()[0]

    cr.execute(
        """
        UPDATE mc_rov_linea_falla lf
           SET causa_raiz = ro.causa_raiz
          FROM repair_order ro
         WHERE lf.repair_id = ro.id
           AND ro.causa_raiz IS NOT NULL
           AND lf.causa_raiz IS NULL
    """
    )
    copiadas = cr.rowcount

    cr.execute("ALTER TABLE repair_order DROP COLUMN causa_raiz")

    _logger.info(
        "mc_rov 19.0.8.0.0: causa_raiz copiada a %s líneas de trabajo. "
        "%s órdenes tenían causa raíz sin ninguna línea y perdieron el valor.",
        copiadas,
        huerfanas,
    )


def _retirar_items(cr):
    """Elimina item_2 … item_5 de repair.order.

    Cuatro Char sin etiqueta heredados de Studio, con la cantidad fija en el código. Cero
    de las diez órdenes de producción los usó nunca, y la etiqueta original ya era "Ítem 2"
    — no había nada que recuperar. Los reemplaza mc_items_recibidos_ids, un Many2many a
    stock.lot: sin tope y trazable, porque los e-pods llevan número de serie propio.
    """
    for columna in COLUMNAS_RETIRADAS:
        if _existe_columna(cr, "repair_order", columna):
            cr.execute(f"ALTER TABLE repair_order DROP COLUMN {columna}")
            _logger.info("mc_rov 19.0.8.0.0: columna repair_order.%s eliminada.", columna)


def _recalcular_ficha_completa(env):
    """Vuelve a calcular mc_ficha_completa en todos los números de serie.

    Es obligatorio y es la trampa de siempre: **el ORM solo rellena columnas nuevas.** Como
    mc_ficha_completa ya existía desde 19.0.6.0.0, agregarle mc_tiene_horometro a su lista
    de campos esenciales no dispara ningún recálculo — las fichas que hoy figuran completas
    seguirían figurando completas para siempre, sin el horómetro.

    Se usa add_to_compute y no un UPDATE en SQL porque la regla vive en Python y duplicarla
    aquí garantizaría que las dos versiones se separen en el próximo cambio.
    """
    Lot = env["stock.lot"]
    lots = Lot.search([])
    if not lots:
        return
    env.add_to_compute(lots._fields["mc_ficha_completa"], lots)
    _logger.info(
        "mc_rov 19.0.8.0.0: mc_ficha_completa marcado para recálculo en %s números de serie.",
        len(lots),
    )


def migrate(cr, version):
    """Prepara la orden de reparación para el protocolo de pruebas.

    Tres pasos independientes, en orden de riesgo creciente: primero se rescata el dato que
    se mueve, después se eliminan las columnas que ya nadie usa, y al final se fuerza el
    recálculo del campo derivado que gana un ingrediente.
    """
    _bajar_causa_raiz(cr)
    _retirar_items(cr)

    env = api.Environment(cr, SUPERUSER_ID, {})
    _recalcular_ficha_completa(env)
