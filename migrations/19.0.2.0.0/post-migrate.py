import logging

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Deben coincidir con models/stock_lot.py
ROV_CATEG_PARAM = "mc_rov.rov_category_id"
ROV_CATEG_XMLID_MODULE = "__import__"
ROV_CATEG_XMLID_NAME = "cat_ROV"


def _resolve_root_category(cr):
    """Devuelve el id de la categoría raíz de vehículos ROV, o None.

    Mismo orden de precedencia que stock.lot._get_rov_root_category, pero en SQL:
    en post-migrate el registro del ORM todavía no es de fiar para este modelo.
    """
    cr.execute("SELECT value FROM ir_config_parameter WHERE key = %s", (ROV_CATEG_PARAM,))
    row = cr.fetchone()
    if row and row[0]:
        try:
            candidate = int(row[0])
        except ValueError:
            _logger.warning(
                "%s tiene un valor no numérico (%r); se ignora.", ROV_CATEG_PARAM, row[0]
            )
        else:
            cr.execute("SELECT id FROM product_category WHERE id = %s", (candidate,))
            if cr.fetchone():
                return candidate
            _logger.warning(
                "%s apunta a la categoría %s, que no existe.", ROV_CATEG_PARAM, candidate
            )

    cr.execute(
        """
        SELECT res_id FROM ir_model_data
        WHERE module = %s AND name = %s AND model = 'product.category'
    """,
        (ROV_CATEG_XMLID_MODULE, ROV_CATEG_XMLID_NAME),
    )
    row = cr.fetchone()
    return row[0] if row else None


def _abortar_si_hay_datos_en_riesgo(cr, motivo):
    """Corta el upgrade solo si hay series marcadas que perderían la marca.

    Sin raíz resoluble el compute apagaría es_un_rov en todo el sistema. Eso importa
    cuando alguien ya cargó fichas técnicas; en una base sin ROVs marcados no hay nada
    que proteger y hacer fallar el upgrade sería ruido.
    """
    cr.execute("SELECT COUNT(*) FROM stock_lot WHERE es_un_rov IS TRUE")
    marcadas = cr.fetchone()[0]

    if marcadas:
        raise UserError(
            f"mc_rov 19.0.2.0.0: {motivo}\n\n"
            f"Hay {marcadas} número(s) de serie marcados como ROV que perderían la marca "
            "y ocultarían su ficha técnica.\n\n"
            "La migración se abortó sin modificar datos."
        )

    _logger.warning(
        "mc_rov 19.0.2.0.0: %s No hay series marcadas como ROV, así que no se aborta: "
        "no hay datos que perder.",
        motivo.replace("\n", " "),
    )


def migrate(cr, version):
    """Convierte es_un_rov de booleano manual a derivado de la categoría del producto.

    El ORM no recalcula un campo que pasa a ser computed+store si la columna ya existía
    con datos: solo rellena columnas nuevas. Sin este UPDATE el cambio aplicaría a los
    números de serie nuevos y los viejos conservarían su valor manual para siempre.

    Si no puede resolver la raíz, aborta solo cuando hay series marcadas que perderían
    la marca. En una base sin árbol de categorías y sin ROVs marcados —una BD de tests,
    por ejemplo— no hay nada que perder y la migración termina sin hacer nada.
    """
    root_id = _resolve_root_category(cr)
    if root_id is None:
        _abortar_si_hay_datos_en_riesgo(
            cr,
            "no se pudo resolver la categoría raíz de vehículos ROV.\n\n"
            f"Se buscó el parámetro de sistema '{ROV_CATEG_PARAM}' y el ID externo "
            f"'{ROV_CATEG_XMLID_MODULE}.{ROV_CATEG_XMLID_NAME}', sin éxito.\n"
            "Defina el parámetro con el ID de la categoría raíz (Ajustes → Técnico → "
            "Parámetros del sistema) y reintente el upgrade.",
        )
        return

    # parent_path es lo que hace funcionar child_of. Si viniera NULL, el LIKE de abajo
    # daría NULL para todas las filas y apagaría el módulo entero en silencio.
    cr.execute("SELECT parent_path FROM product_category WHERE id = %s", (root_id,))
    row = cr.fetchone()
    if not row or not row[0]:
        _abortar_si_hay_datos_en_riesgo(
            cr,
            f"la categoría raíz {root_id} no tiene parent_path calculado.\n"
            "Ejecute una reconstrucción del árbol de categorías antes de reintentar.",
        )
        return

    # Se siembra el parámetro para que el runtime tenga una sola fuente y el XML ID
    # de la importación quede solo como respaldo.
    cr.execute(
        """
        INSERT INTO ir_config_parameter (key, value, create_uid, create_date, write_uid, write_date)
        VALUES (%s, %s, 1, NOW() AT TIME ZONE 'UTC', 1, NOW() AT TIME ZONE 'UTC')
        ON CONFLICT (key) DO NOTHING
    """,
        (ROV_CATEG_PARAM, str(root_id)),
    )

    # Cuántas series pierden la marca, para que quede constancia en el log del deploy
    cr.execute(
        """
        SELECT COUNT(*)
          FROM stock_lot sl
          JOIN product_product pp ON pp.id = sl.product_id
          JOIN product_template pt ON pt.id = pp.product_tmpl_id
          JOIN product_category pc ON pc.id = pt.categ_id
         WHERE sl.es_un_rov IS TRUE
           AND COALESCE(pc.parent_path LIKE (
                   SELECT parent_path || '%%' FROM product_category WHERE id = %s
               ), FALSE) IS FALSE
    """,
        (root_id,),
    )
    apagados = cr.fetchone()[0]

    cr.execute(
        """
        UPDATE stock_lot sl
           SET es_un_rov = COALESCE(pc.parent_path LIKE (
                   SELECT parent_path || '%%' FROM product_category WHERE id = %s
               ), FALSE)
          FROM product_product pp
          JOIN product_template pt ON pt.id = pp.product_tmpl_id
          JOIN product_category pc ON pc.id = pt.categ_id
         WHERE sl.product_id = pp.id
    """,
        (root_id,),
    )

    _logger.info(
        "mc_rov: es_un_rov recalculado sobre %s números de serie usando la categoría raíz %s. "
        "%s perdieron la marca manual por quedar fuera de la rama ROV.",
        cr.rowcount,
        root_id,
        apagados,
    )
