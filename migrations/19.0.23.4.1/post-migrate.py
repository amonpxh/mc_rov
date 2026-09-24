"""Acorta el nombre del chequeo instalado sin pisar una edición del taller.

El catálogo usa ``noupdate=1``: el XML nuevo solo afecta instalaciones nuevas. En las
existentes se renombra el registro por XML ID si aún lleva exactamente el texto anterior.
"""


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        UPDATE mc_rov_chequeo AS chequeo
           SET name = %s
          FROM ir_model_data AS identifier
         WHERE identifier.module = 'mc_rov'
           AND identifier.model = 'mc.rov.chequeo'
           AND identifier.name = 'chequeo_salida_brazo'
           AND identifier.res_id = chequeo.id
           AND chequeo.name = %s
        """,
        (
            "Salida de brazo funcionando correctamente",
            "Salida de brazo configurada, reconocida en software y operativa "
            "con brazos de corte y pinza",
        ),
    )
