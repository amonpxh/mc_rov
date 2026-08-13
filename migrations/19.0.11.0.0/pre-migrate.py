import logging

_logger = logging.getLogger(__name__)

# Los cinco modelos que cambian de nombre. En orden de borrado: primero las líneas, que
# tienen clave foránea hacia la cabecera.
MODELOS_VIEJOS = [
    "mc.rov.protocolo.inspeccion",
    "mc.rov.protocolo.hallazgo",
    "mc.rov.protocolo.chequeo",
    "mc.rov.protocolo.corrida",
    "mc.rov.protocolo",
]
TABLAS_VIEJAS = [modelo.replace(".", "_") for modelo in MODELOS_VIEJOS]


def _contar(cr, tabla):
    cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = %s", (tabla,))
    if not cr.fetchone():
        return None
    cr.execute(f"SELECT COUNT(*) FROM {tabla}")
    return cr.fetchone()[0]


def migrate(cr, version):
    """Descarta los modelos «protocolo» para que el ORM cree los «revisión» limpios.

    El renombre es de nombre, no de estructura: los campos y las relaciones son idénticos.
    Conservar los datos exigiría reescribir seis tablas de sistema —ir_model,
    ir_model_fields, ir_model_data, ir_model_relation, más el res_model de mail_message y
    el de las vistas— y errarle a una sola deja rastros invisibles: chatter huérfano,
    adjuntos que apuntan a un modelo que ya no existe.

    Cuando se escribió esto, producción tenía **1 registro de prueba con 22 líneas de
    checklist y ningún hallazgo**, creado el mismo día para mirar la pantalla. Esa cirugía
    no se justifica por eso, así que se descarta y se empieza limpio.

    **Si alguien despliega esta versión con revisiones de verdad, las va a perder.** El
    conteo queda en el log para que se note.
    """
    for tabla in TABLAS_VIEJAS:
        filas = _contar(cr, tabla)
        if filas is None:
            continue
        _logger.warning(
            "mc_rov 19.0.11.0.0: se descarta la tabla %s con %s fila(s) por el renombre "
            "a «revisión».",
            tabla,
            filas,
        )

    # El CASCADE se lleva la clave foránea de mc_rov_linea_falla.hallazgo_origen_id; la
    # columna sobrevive con ids muertos, así que se vacía antes de que el ORM la vuelva a
    # apuntar al modelo nuevo.
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'mc_rov_linea_falla' AND column_name = 'hallazgo_origen_id'
    """
    )
    if cr.fetchone():
        cr.execute("UPDATE mc_rov_linea_falla SET hallazgo_origen_id = NULL")

    for tabla in TABLAS_VIEJAS:
        cr.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")

    # La metadata del ORM. Sin esto Odoo conserva modelos cuya tabla ya no existe y falla
    # al construir el registro.
    cr.execute("DELETE FROM ir_model_fields WHERE model = ANY(%s)", (MODELOS_VIEJOS,))
    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.model' AND res_id IN "
        "(SELECT id FROM ir_model WHERE model = ANY(%s))",
        (MODELOS_VIEJOS,),
    )
    cr.execute("DELETE FROM ir_model WHERE model = ANY(%s)", (MODELOS_VIEJOS,))

    # Vistas, acciones y menús del nombre viejo. Sus XML ID desaparecieron del módulo, así
    # que Odoo los borraría igual — pero antes intentaría cargarlos contra un modelo que ya
    # no existe.
    cr.execute(
        """
        DELETE FROM ir_ui_view WHERE model = ANY(%s);
    """,
        (MODELOS_VIEJOS,),
    )
    cr.execute(
        """
        DELETE FROM ir_act_window WHERE res_model = ANY(%s);
    """,
        (MODELOS_VIEJOS,),
    )
    cr.execute("DELETE FROM ir_sequence WHERE code = 'mc.rov.protocolo'")

    _logger.info("mc_rov 19.0.11.0.0: modelos «protocolo» retirados. El ORM creará «revisión».")
