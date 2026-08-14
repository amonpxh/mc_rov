"""19.0.12.0.0 — una sola revisión por visita.

Tres trabajos, todos ANTES de que Odoo cargue el módulo. El orden importa: los archivos de
datos se cargan entre el pre-migrate y el post-migrate, así que lo que se deja arreglado
aquí es lo que el XML encuentra, y los valores declarados en el XML ganan sobre lo que este
script haya escrito. Al revés —en post-migrate— este script pisaría el catálogo recién
cargado.

Los tres son de tipo "esto ya no existe":

1. `aplica_recepcion` y `aplica_entrega` del catálogo de chequeos se fusionan en
   `aplica_reparacion`. La columna se crea a mano porque el ORM crea las columnas nuevas
   después del pre-migrate, y para entonces ya sería tarde para leer las viejas.
2. Los tipos `recepcion` y `entrega` de las revisiones colapsan en `reparacion`.
3. El chequeo "Marcas de plumón" sale de la batería.
"""

import logging

_logger = logging.getLogger(__name__)


def _fusionar_aplica(cr):
    """aplica_recepcion OR aplica_entrega -> aplica_reparacion.

    Un chequeo que se corría en recepción o en entrega se corre ahora en la reparación, que
    es la única revisión que hay. El OR y no el AND: perder un chequeo de la batería es
    peor que correr uno de más.
    """
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'mc_rov_chequeo' AND column_name = 'aplica_recepcion'
        """
    )
    if not cr.fetchone():
        _logger.info("mc_rov: aplica_recepcion ya no existe, nada que fusionar")
        return

    cr.execute("ALTER TABLE mc_rov_chequeo ADD COLUMN IF NOT EXISTS aplica_reparacion boolean")
    cr.execute(
        """
        UPDATE mc_rov_chequeo
           SET aplica_reparacion = COALESCE(aplica_recepcion, false)
                                OR COALESCE(aplica_entrega, false)
        """
    )
    _logger.info("mc_rov: %s chequeos con aplica_reparacion resuelto", cr.rowcount)

    cr.execute(
        """
        ALTER TABLE mc_rov_chequeo
            DROP COLUMN IF EXISTS aplica_recepcion,
            DROP COLUMN IF EXISTS aplica_entrega
        """
    )


def _colapsar_tipos(cr):
    """recepcion y entrega pasan a reparacion.

    `tipo` es un Selection, o sea un varchar: basta el UPDATE. La tabla de inspección lleva
    una copia almacenada del mismo valor (related store=True) y hay que moverla igual, o el
    related queda contradiciendo a su origen hasta el próximo recálculo.
    """
    for tabla in ("mc_rov_revision", "mc_rov_revision_inspeccion"):
        cr.execute(
            f"UPDATE {tabla} SET tipo = 'reparacion' WHERE tipo IN ('recepcion', 'entrega')"
        )
        _logger.info("mc_rov: %s filas de %s pasaron a tipo 'reparacion'", cr.rowcount, tabla)


def _retirar_chequeo_plumon(cr):
    """Saca "Marcas de plumón" de la batería, líneas primero.

    El orden no es cosmético: `chequeo_id` es ondelete="restrict", así que borrar el
    registro de catálogo con líneas colgando falla. Y hay que borrarlo aquí y no dejárselo a
    la limpieza de datos obsoletos de Odoo, que ante ese mismo error se rinde en silencio y
    deja el chequeo en el catálogo para siempre.

    Ver una marca de plumón sigue siendo registrable: el hallazgo del mismo nombre se queda.
    Lo que se retira es preguntarlo en los cinco componentes de cada revisión.
    """
    cr.execute(
        """
        SELECT res_id FROM ir_model_data
         WHERE module = 'mc_rov' AND name = 'chequeo_plumon'
        """
    )
    fila = cr.fetchone()
    if not fila:
        _logger.info("mc_rov: chequeo_plumon no está en la base, nada que retirar")
        return

    chequeo_id = fila[0]

    cr.execute("DELETE FROM mc_rov_revision_chequeo WHERE chequeo_id = %s", (chequeo_id,))
    _logger.info("mc_rov: %s líneas de marcas de plumón eliminadas", cr.rowcount)

    cr.execute("DELETE FROM mc_rov_chequeo WHERE id = %s", (chequeo_id,))
    cr.execute("DELETE FROM ir_model_data WHERE module = 'mc_rov' AND name = 'chequeo_plumon'")


def migrate(cr, version):
    if not version:
        return

    _fusionar_aplica(cr)
    _colapsar_tipos(cr)
    _retirar_chequeo_plumon(cr)
