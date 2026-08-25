"""19.0.23.0.0 — se archivan las causas de calidad que trae Odoo.

`quality_control` entrega cuatro: *Falla en el centro de trabajo*, *Operación de trabajo*,
*Calidad de las piezas* y *Otros*. Contestan **dónde ocurrió** el problema. Las seis que
`19.0.22.2.0` agregó contestan otra cosa — **de quién es** — y hay solape real: «Calidad de
las piezas» pisa a *Pieza de proveedor*, y «Falla en el centro de trabajo» y «Operación de
trabajo» pisan a *Manufactura propia*.

**Diez opciones donde tres significan casi lo mismo que otras dos no es un catálogo más rico,
es un conteo que después no significa nada.** Es el problema de las cuatro formas de escribir
«no enciende», y la razón por la que el catálogo de síntomas se cerró en `19.0.13.0.0`.

**Se archivan, no se borran.** Si alguna alerta vieja las usara, borrarlas se llevaría el
dato; archivadas, la alerta las sigue mostrando y el catálogo deja de ofrecerlas. Y se
deshace desde la pantalla: Calidad → Configuración → Causas, quitar el filtro y
desarchivar.

**Y archivar solo se puede porque este módulo le agrega `active` al modelo.** Odoo lo entrega
sin él —lo descubrió este mismo script en el ensayo, que encontró la columna ausente y se
detuvo sin tocar nada— así que un catálogo que Odoo no deja retirar se estaba llamando «del
usuario». Ver `models/quality_reason.py`.

**No se resuelven por XML ID a propósito.** Nombrar `quality_control.quality_reason_X` obliga
a acertar cuatro identificadores de otro módulo, y equivocar uno impide instalar el módulo
entero. En vez de eso se archiva *lo que tenga XML ID de un módulo que no sea el nuestro*: es
exactamente el conjunto de las que vienen de fábrica, porque las que crea una persona desde
la pantalla no tienen XML ID ninguno. **Un catálogo que el taller agregue a mano no se toca.**

Lo pidió Paulo el 2026-08-25 después de ver las diez juntas en el desplegable.
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
    """Sin `version` es una instalación limpia.

    En una instalación limpia esto no corre, así que las cuatro de Odoo quedarían activas.
    Se acepta: hay una sola instancia y es una actualización. Si algún día se instala de
    cero en otra parte, se archivan a mano desde el menú — que existe justamente para eso.
    """
    if not version:
        return

    if not _existe_columna(cr, "quality_reason", "active"):
        _logger.warning(
            "mc_rov 19.0.23.0.0: quality.reason no tiene campo `active`, así que las causas "
            "de Odoo no se pueden archivar. Quedan las diez en el desplegable."
        )
        return

    cr.execute(
        """
        UPDATE quality_reason SET active = false
        WHERE active
          AND id IN (
              SELECT res_id FROM ir_model_data
              WHERE model = 'quality.reason' AND module <> 'mc_rov'
          )
        """
    )
    _logger.info("mc_rov 19.0.23.0.0: %s causa(s) de calidad de Odoo archivadas", cr.rowcount)

    cr.execute("SELECT count(*) FROM quality_reason WHERE active")
    _logger.info(
        "mc_rov 19.0.23.0.0: quedan %s causa(s) activas — deberían ser las seis nuestras",
        cr.fetchone()[0],
    )
