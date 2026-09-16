"""Completa etiquetas de cliente sin sobrescribir el catálogo del taller.

Los valores viven en el XML semilla, también para instalaciones nuevas. Se leen
desde allí porque noupdate protege los registros existentes durante una actualización.
"""

from pathlib import Path

from lxml import etree


def migrate(cr, version):
    if not version:
        return
    source = Path(__file__).resolve().parents[2] / "data" / "mc_rov_revision_data.xml"
    document = etree.parse(str(source))
    for record in document.xpath("//record[@model='mc.rov.chequeo']"):
        label = record.find("field[@name='nombre_ficha']")
        if label is None or not label.text:
            continue
        cr.execute(
            """
            UPDATE mc_rov_chequeo AS chequeo
               SET nombre_ficha = %s
              FROM ir_model_data AS identifier
             WHERE identifier.module = 'mc_rov'
               AND identifier.model = 'mc.rov.chequeo'
               AND identifier.name = %s
               AND identifier.res_id = chequeo.id
               AND COALESCE(BTRIM(chequeo.nombre_ficha), '') = ''
            """,
            (label.text, record.get("id")),
        )
