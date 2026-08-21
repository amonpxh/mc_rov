"""19.0.20.0.0 — el reparto de las tres baterías, y el catálogo pasa a ser del usuario.

Bloque A4, con la batería de armado ya descartada (ver `docs/pendientes.md`). Quedan las tres
que viven en `mc.rov.revision`: **rendimiento 18 · terreno 17 · reparación 24**, según el § 5.3
del diseño de fabricación.

**Por qué hace falta un script y no basta con el XML.** En esta misma versión el catálogo de
chequeos pasa a `noupdate="1"`, para que un ajuste hecho desde Configuración sobreviva a la
próxima actualización del módulo. El efecto inmediato es que Odoo **deja de aplicar** los
valores del XML a los registros que ya existen — o sea que sin este script el reparto nuevo
saldría solo en instalaciones limpias, y producción se quedaría con los 22 · 22 · 24 de antes.

Es la única vez que hace falta: de aquí en adelante el catálogo se ajusta en pantalla.
"""

import logging

_logger = logging.getLogger(__name__)

# Qué cambia respecto de 19.0.19.0.0, por XML ID. Reparación no aparece porque no cambia:
# sigue con los 24 — es la batería del equipo que llegó roto y ahí se mira todo.
CAMBIOS = {
    # Buscan daño de uso o desgaste: un equipo recién armado no lo tiene.
    "chequeo_chasis": {"aplica_rendimiento": False, "aplica_terreno": False},
    "chequeo_penetradores": {"aplica_rendimiento": False, "aplica_terreno": False},
    "chequeo_helices_dano": {"aplica_rendimiento": False, "aplica_terreno": False},
    "chequeo_umbilical_estado": {"aplica_rendimiento": False, "aplica_terreno": False},
    # La posición de las hélices ya se verifica funcionalmente en rendimiento.
    "chequeo_helices": {"aplica_rendimiento": False, "aplica_terreno": False},
    # Se había acotado de más a reparación en 19.0.15.2.0.
    "chequeo_software_opera": {"aplica_rendimiento": True, "aplica_terreno": True},
    # En el muelle no hay máquina de presión: ahí la misma pregunta la contesta la
    # profundidad alcanzada.
    "chequeo_estanqueidad": {"aplica_terreno": False},
}


def _id_de(cr, nombre):
    cr.execute(
        "SELECT res_id FROM ir_model_data WHERE module = 'mc_rov' AND name = %s "
        "AND model = 'mc.rov.chequeo'",
        (nombre,),
    )
    fila = cr.fetchone()
    return fila[0] if fila else None


def migrate(cr, version):
    """Sin `version` es una instalación limpia: el XML ya trae el reparto correcto."""
    if not version:
        return

    tocados = 0
    for nombre, campos in CAMBIOS.items():
        res_id = _id_de(cr, nombre)
        if not res_id:
            _logger.warning(
                "mc_rov 19.0.20.0.0: no existe el chequeo %s, se omite. Si alguien lo borró "
                "del catálogo, el reparto de su batería queda como estaba.",
                nombre,
            )
            continue

        # Se registra el valor anterior antes de escribir: si alguien ya lo había ajustado a
        # mano, este script lo pisa una única vez, y el log es lo que permite darse cuenta.
        columnas = ", ".join(campos)
        cr.execute(f"SELECT {columnas} FROM mc_rov_chequeo WHERE id = %s", (res_id,))
        antes = dict(zip(campos, cr.fetchone()))
        if antes == campos:
            continue

        asignaciones = ", ".join(f"{campo} = %s" for campo in campos)
        cr.execute(
            f"UPDATE mc_rov_chequeo SET {asignaciones} WHERE id = %s",
            list(campos.values()) + [res_id],
        )
        _logger.info("mc_rov 19.0.20.0.0: %s pasa de %s a %s", nombre, antes, dict(campos))
        tocados += 1

    _logger.info("mc_rov 19.0.20.0.0: %s chequeo(s) cambiaron de batería", tocados)

    # Y el recuento final, que es lo que hay que mirar: 18 · 17 · 24.
    cr.execute(
        "SELECT count(*) FILTER (WHERE aplica_rendimiento), "
        "count(*) FILTER (WHERE aplica_terreno), "
        "count(*) FILTER (WHERE aplica_reparacion) FROM mc_rov_chequeo"
    )
    _logger.info("mc_rov 19.0.20.0.0: rendimiento %s · terreno %s · reparación %s", *cr.fetchone())
