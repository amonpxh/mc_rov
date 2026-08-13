import logging

_logger = logging.getLogger(__name__)

# Los dos campos que pasan de Selection (varchar) a Many2one (integer).
CAMPOS = ("mc_software_superficie", "mc_controlador_vuelo")


def _existe_columna(cr, columna):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'stock_lot' AND column_name = %s
    """,
        (columna,),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    """Aparta las columnas de texto antes de que el ORM cree las nuevas.

    Odoo **no convierte el tipo de una columna** cuando un campo cambia de Selection a
    Many2one: se encuentra un varchar donde espera un integer, registra una advertencia y
    deja la columna como está. El resultado sería un campo permanentemente roto.

    El patrón es renombrar aquí, dejar que la carga del módulo cree la columna integer
    limpia, y traducir los valores en post-migrate, cuando los registros del catálogo ya
    existen porque los archivos de datos cargan antes.
    """
    for campo in CAMPOS:
        if not _existe_columna(cr, campo):
            _logger.info("mc_rov 19.0.9.0.0: %s ya fue apartada.", campo)
            continue
        if _existe_columna(cr, f"{campo}_texto"):
            cr.execute(f"ALTER TABLE stock_lot DROP COLUMN {campo}")
            continue
        cr.execute(f"ALTER TABLE stock_lot RENAME COLUMN {campo} TO {campo}_texto")
        _logger.info("mc_rov 19.0.9.0.0: stock_lot.%s apartada como %s_texto.", campo, campo)
