import logging

from psycopg2 import sql

_logger = logging.getLogger(__name__)

MOTIVO_BAJA_MIGRADA = (
    "Baja migrada desde el estado comercial anterior. La fecha es aproximada: se usó la "
    "última modificación del número de serie porque el sistema no guardaba cuándo "
    "ocurrió la baja. Corríjala si conoce la fecha real."
)


def _convertir_bajas(cr):
    """Rescata las bajas antes de que el recálculo borre el valor manual.

    Este paso va primero y no es opcional. mc_estado_comercial pasa a calcularse a
    partir de mc_fecha_baja, así que si el recálculo corriera antes, los equipos que
    alguien marcó como "Baja" volverían a decir "Disponible" y no quedaría de dónde
    reconstruirlo.

    Se inventa una fecha, cosa que el módulo evita por norma. Aquí es el mal menor: el
    hecho de que el equipo está de baja importa más que el día exacto, y perderlo sería
    irreversible. El motivo deja constancia de que la fecha es aproximada para que nadie
    la lea como un dato registrado.
    """
    cr.execute(
        """
        UPDATE stock_lot
           SET mc_fecha_baja = COALESCE(write_date::date, create_date::date, CURRENT_DATE),
               mc_motivo_baja = %s
         WHERE mc_estado_comercial = 'Baja'
           AND mc_fecha_baja IS NULL
    """,
        (MOTIVO_BAJA_MIGRADA,),
    )
    return cr.rowcount


def _sembrar_propietarios(cr):
    """Deja todo número de serie sin propietario a nombre de la empresa.

    Vacío no puede significar "es nuestro": no se distinguiría de "nadie lo llenó", y
    el estado comercial se calcula comparando contra el contacto de la compañía.
    """
    cr.execute(
        """
        UPDATE stock_lot sl
           SET mc_propietario_id = rc.partner_id
          FROM res_company rc
         WHERE rc.id = COALESCE(sl.company_id, (SELECT MIN(id) FROM res_company))
           AND sl.mc_propietario_id IS NULL
    """
    )
    return cr.rowcount


def _sembrar_historial(cr):
    """Abre el primer período de propiedad de cada ROV existente.

    Sin esto, el historial de un equipo empezaría recién en su primer traspaso y el
    período en que fue de la empresa no aparecería por ninguna parte. La fecha de
    creación del número de serie es lo más cercano que hay a cuándo empezó.

    Solo ROVs, igual que el override de create: los lotes de componentes también tienen
    propietario, pero abrirles historial llenaría la tabla de filas inútiles.
    """
    cr.execute(
        """
        INSERT INTO mc_rov_propietario_historial
               (lot_id, partner_id, fecha_desde,
                create_uid, create_date, write_uid, write_date)
        SELECT sl.id,
               sl.mc_propietario_id,
               COALESCE(sl.create_date::date, CURRENT_DATE),
               1, NOW() AT TIME ZONE 'UTC', 1, NOW() AT TIME ZONE 'UTC'
          FROM stock_lot sl
         WHERE sl.es_un_rov IS TRUE
           AND sl.mc_propietario_id IS NOT NULL
           AND NOT EXISTS (
                 SELECT 1 FROM mc_rov_propietario_historial h WHERE h.lot_id = sl.id
           )
    """
    )
    return cr.rowcount


def _relacion_many2many(cr, campo):
    """Nombre real de la tabla intermedia y sus columnas, según Odoo.

    Se lee de ir_model_fields en vez de escribirlo a mano porque son detalles internos
    de sale_stock_renting: si cambiaran de nombre entre versiones, hardcodearlos haría
    que la migración marcara mal los arriendos sin fallar.
    """
    cr.execute(
        """
        SELECT relation_table, column1, column2
          FROM ir_model_fields
         WHERE model = 'sale.order.line' AND name = %s
    """,
        (campo,),
    )
    row = cr.fetchone()
    if not row or not all(row):
        return None
    return row


def _marcar_arriendos(cr):
    """Marca "En arriendo" los equipos retirados y no devueltos.

    Solo pisa a los que quedaron "Disponible": un equipo vendido sigue siendo del
    cliente aunque además esté arrendado, y la baja se aplica después de esto.

    Si no logra resolver las tablas, no marca nada y avisa. El estado se corregirá solo
    la próxima vez que se toque la línea de arriendo, gracias al override de write de
    sale.order.line.
    """
    retirados = _relacion_many2many(cr, "pickedup_lot_ids")
    devueltos = _relacion_many2many(cr, "returned_lot_ids")
    if not retirados or not devueltos:
        _logger.warning(
            "mc_rov 19.0.5.0.0: no se pudieron resolver las tablas de arriendo de "
            "sale_stock_renting. Ningún equipo quedó marcado 'En arriendo'; se "
            "corregirán al tocar sus líneas de arriendo."
        )
        return 0

    tabla_ret, col_linea_ret, col_lote_ret = retirados
    tabla_dev, col_linea_dev, col_lote_dev = devueltos

    cr.execute(
        sql.SQL(
            """
        UPDATE stock_lot
           SET mc_estado_comercial = 'En arriendo'
         WHERE mc_estado_comercial = 'Disponible'
           AND id IN (
                 SELECT p.{lote_ret}
                   FROM {tabla_ret} p
                   JOIN sale_order_line sol ON sol.id = p.{linea_ret}
                  WHERE sol.is_rental IS TRUE
                    AND sol.state <> 'cancel'
                    AND NOT EXISTS (
                          SELECT 1 FROM {tabla_dev} d
                           WHERE d.{linea_dev} = p.{linea_ret}
                             AND d.{lote_dev} = p.{lote_ret}
                    )
           )
    """
        ).format(
            tabla_ret=sql.Identifier(tabla_ret),
            linea_ret=sql.Identifier(col_linea_ret),
            lote_ret=sql.Identifier(col_lote_ret),
            tabla_dev=sql.Identifier(tabla_dev),
            linea_dev=sql.Identifier(col_linea_dev),
            lote_dev=sql.Identifier(col_lote_dev),
        )
    )
    return cr.rowcount


def _recalcular_estado_comercial(cr):
    """Recalcula el campo, que deja de ser manual.

    El ORM no recalcula un campo que pasa a ser computed+store si la columna ya existía
    con datos: solo rellena columnas nuevas. Sin esto los números de serie conservarían
    el valor escrito a mano para siempre.

    El orden replica el de _compute_mc_estado_comercial en models/stock_lot.py: la baja
    gana sobre todo, y un equipo vendido no vuelve a decir "Disponible".
    """
    cr.execute("UPDATE stock_lot SET mc_estado_comercial = 'Disponible'")
    total = cr.rowcount

    cr.execute(
        """
        UPDATE stock_lot sl
           SET mc_estado_comercial = 'Vendido'
          FROM res_company rc
         WHERE rc.id = COALESCE(sl.company_id, (SELECT MIN(id) FROM res_company))
           AND sl.mc_propietario_id IS NOT NULL
           AND sl.mc_propietario_id <> rc.partner_id
    """
    )
    vendidos = cr.rowcount

    arrendados = _marcar_arriendos(cr)

    cr.execute("UPDATE stock_lot SET mc_estado_comercial = 'Baja' WHERE mc_fecha_baja IS NOT NULL")
    de_baja = cr.rowcount

    return total, vendidos, arrendados, de_baja


def migrate(cr, version):
    """Convierte mc_estado_comercial en derivado e introduce la propiedad del equipo.

    El orden de los pasos es la parte frágil: las bajas se rescatan antes del recálculo
    y los propietarios se siembran antes de que se decida quién está "Vendido".

    No lleva portón de aborto como 19.0.2.0.0 porque no se pierde nada que no sea
    reconstruible: el estado se deriva del propietario y de la baja, que quedan ambos
    guardados en columnas propias.
    """
    bajas = _convertir_bajas(cr)
    propietarios = _sembrar_propietarios(cr)
    periodos = _sembrar_historial(cr)
    total, vendidos, arrendados, de_baja = _recalcular_estado_comercial(cr)

    _logger.info(
        "mc_rov: %s bajas rescatadas del estado comercial, %s números de serie quedaron "
        "a nombre de la empresa, %s períodos de propiedad abiertos.",
        bajas,
        propietarios,
        periodos,
    )
    _logger.info(
        "mc_rov: mc_estado_comercial recalculado sobre %s números de serie. "
        "%s vendidos, %s en arriendo, %s de baja, el resto disponibles.",
        total,
        vendidos,
        arrendados,
        de_baja,
    )
