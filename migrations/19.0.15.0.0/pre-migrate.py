"""19.0.15.0.0 — una corrida por revisión.

`mc.rov.revision.corrida` era un modelo de línea: una revisión podía tener varias corridas,
una por umbilical, para poder comparar cables dentro de la misma ficha. Desaparece y sus
campos suben a `mc.rov.revision`.

**La razón por la que estaban abajo resultó ser falsa a medias.** El diseño decía que «lo que
no depende del cable vive en la revisión y se hace una sola vez aunque haya dos corridas». Pero
varios chequeos sí dependen del cable —responde a comandos, ancho de banda, probablemente
video— y las dos corridas compartían **un solo juego de respuestas**: cualquier chequeo que
cambiara entre un cable y otro se perdía en silencio, y la comparación quedaba visible en
cuatro números y en nada más.

Ahora una revisión es una prueba completa bajo una condición. Comparar dos cables son dos
revisiones, cada una con su batería, y `motivo` distingue esa comparación de un re-test tras
reparación.

**Qué pasa con las revisiones que tenían más de una corrida.** No se pueden convertir en dos
revisiones: la segunda necesitaría su propio juego de 22 respuestas, y esas respuestas no
existen — nunca se llenaron por separado, que es justamente el defecto que motiva este cambio.
Así que se sube la **primera** corrida y las demás se vuelcan al log antes de borrarlas, para
que nadie descubra meses después que había datos y se fueron sin aviso.
"""

import logging

_logger = logging.getLogger(__name__)

# Los campos que suben tal cual, con el mismo nombre en las dos tablas.
CAMPOS = [
    "umbilical",
    "largo",
    "alimentacion",
    "tension_salida",
    "esfuerzo_duracion",
    "esfuerzo_resultado",
    "subida",
    "bajada",
    "temperatura_interior",
    "temperatura_exterior",
]


def _existe_tabla(cr, tabla):
    cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = %s", (tabla,))
    return bool(cr.fetchone())


def _avisar_de_las_que_se_pierden(cr):
    """Vuelca al log las corridas que no son la primera de su revisión.

    Son las únicas que se pierden, y se pierden porque no hay dónde ponerlas: convertirlas en
    revisiones nuevas exigiría inventarles las respuestas del checklist.
    """
    cr.execute(
        """
        SELECT c.revision_id, r.name, c.umbilical, c.largo, c.esfuerzo_resultado,
               c.esfuerzo_duracion, c.subida, c.bajada
          FROM mc_rov_revision_corrida c
          JOIN mc_rov_revision r ON r.id = c.revision_id
         WHERE c.id <> (
                   SELECT id FROM mc_rov_revision_corrida
                    WHERE revision_id = c.revision_id
                    ORDER BY sequence, id LIMIT 1
               )
         ORDER BY c.revision_id, c.sequence, c.id
        """
    )
    filas = cr.fetchall()
    if not filas:
        _logger.info("mc_rov 19.0.15.0.0: ninguna revisión tenía más de una corrida")
        return

    _logger.warning(
        "mc_rov 19.0.15.0.0: %s corrida(s) adicionales se descartan al colapsar el modelo. "
        "Se listan a continuación para que el dato no desaparezca sin registro.",
        len(filas),
    )
    for fila in filas:
        _logger.warning("mc_rov 19.0.15.0.0: corrida descartada -> %s", fila)


def _subir_la_primera(cr):
    """Copia la primera corrida de cada revisión a su cabecera.

    Las columnas se crean a mano porque el ORM las crearía después del pre-migrate, y para
    entonces la tabla de origen ya no estaría.
    """
    tipos = {
        "umbilical": "varchar",
        "largo": "double precision",
        "alimentacion": "varchar",
        "tension_salida": "integer",
        "esfuerzo_duracion": "double precision",
        "esfuerzo_resultado": "varchar",
        "subida": "double precision",
        "bajada": "double precision",
        "temperatura_interior": "double precision",
        "temperatura_exterior": "double precision",
    }
    for campo, tipo in tipos.items():
        cr.execute(f"ALTER TABLE mc_rov_revision ADD COLUMN IF NOT EXISTS {campo} {tipo}")

    asignaciones = ", ".join(f"{campo} = c.{campo}" for campo in CAMPOS)
    cr.execute(
        f"""
        UPDATE mc_rov_revision r
           SET {asignaciones}
          FROM mc_rov_revision_corrida c
         WHERE c.revision_id = r.id
           AND c.id = (
                   SELECT id FROM mc_rov_revision_corrida
                    WHERE revision_id = r.id
                    ORDER BY sequence, id LIMIT 1
               )
        """
    )
    _logger.info("mc_rov 19.0.15.0.0: %s revisión(es) recibieron su corrida", cr.rowcount)


def _retirar_el_modelo(cr):
    """Borra la tabla y la metadata del ORM.

    Sin limpiar `ir_model` y `ir_model_fields`, Odoo conserva un modelo cuya tabla ya no existe
    y falla al construir el registro. Es la misma limpieza que hizo 19.0.11.0.0 con los
    modelos «protocolo».
    """
    cr.execute("DROP TABLE IF EXISTS mc_rov_revision_corrida CASCADE")
    cr.execute("DELETE FROM ir_model_fields WHERE model = 'mc.rov.revision.corrida'")
    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.model' AND res_id IN "
        "(SELECT id FROM ir_model WHERE model = 'mc.rov.revision.corrida')"
    )
    cr.execute("DELETE FROM ir_model WHERE model = 'mc.rov.revision.corrida'")
    cr.execute("DELETE FROM ir_ui_view WHERE model = 'mc.rov.revision.corrida'")
    cr.execute("DELETE FROM ir_act_window WHERE res_model = 'mc.rov.revision.corrida'")


def migrate(cr, version):
    """Sin `version` es una instalación limpia y no hay nada que migrar."""
    if not version:
        return

    if not _existe_tabla(cr, "mc_rov_revision_corrida"):
        _logger.info("mc_rov 19.0.15.0.0: la corrida ya está en la revisión")
        return

    _avisar_de_las_que_se_pierden(cr)
    _subir_la_primera(cr)
    _retirar_el_modelo(cr)
