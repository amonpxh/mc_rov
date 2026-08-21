"""19.0.19.0.0 — las pruebas de aceptación estrenan numeración propia.

`REV/` se queda con las reparaciones; las pruebas de rendimiento y de terreno pasan a
numerarse `RND/` y `TRN/`. **Las revisiones que ya existen conservan su número**: renumerar
un documento entregado rompe la referencia que el cliente tiene en la mano, y ése es
exactamente el daño que la numeración por tipo viene a evitar. Ver `designs/fabricacion.md`
§ 4.8.

Lo único que hay que migrar es el campo nuevo `documento_emitido`, que es lo que congela el
tipo. Nace en `False`, así que **sin este script toda revisión ya confirmada quedaría con el
tipo abierto** — se la devuelve a borrador, se le cambia el tipo, y se renumera un documento
que ya salió. El campo no puede derivarse de `estado` porque tiene que sobrevivir a que la
revisión vuelva a borrador, que es justamente el caso que hay que cubrir.
"""

import logging

_logger = logging.getLogger(__name__)


def _existe_columna(cr, tabla, columna):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
        (tabla, columna),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    """Sin `version` es una instalación limpia y no hay nada que migrar."""
    if not version:
        return

    if not _existe_columna(cr, "mc_rov_revision", "documento_emitido"):
        _logger.error(
            "mc_rov 19.0.19.0.0: documento_emitido no existe todavía; el ORM debería haberla "
            "creado antes de este script. Las revisiones confirmadas quedan con el tipo "
            "abierto — revisar antes de dar el despliegue por bueno."
        )
        return

    # Lo que ya estaba confirmado ya se emitió. Lo contrario no es cierto en general —una
    # revisión confirmada y devuelta a borrador también se emitió— pero antes de este cambio
    # no había forma de distinguirlas, y volver a borrador es la excepción, no la regla.
    cr.execute("UPDATE mc_rov_revision SET documento_emitido = true WHERE estado = 'confirmado'")
    _logger.info(
        "mc_rov 19.0.19.0.0: %s revisión(es) confirmadas quedan con el tipo congelado",
        cr.rowcount,
    )

    # Y lo que quedó en borrador, para saber a qué atenerse: son las que todavía pueden
    # cambiar de tipo y renumerarse.
    cr.execute("SELECT count(*) FROM mc_rov_revision WHERE estado = 'borrador'")
    _logger.info(
        "mc_rov 19.0.19.0.0: %s revisión(es) siguen en borrador y conservan su número REV/",
        cr.fetchone()[0],
    )
