"""Separa software de electrónica sin dejar un subtipo bajo el componente anterior."""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """El XML mueve Parámetros; sus hallazgos y trabajos deben acompañarlo."""
    if not version:
        return

    ids = {}
    for name, model in (
        ("comp_electronica", "mc.rov.componente"),
        ("comp_software", "mc.rov.componente"),
        ("sub_elec_parametros", "mc.rov.subtipo"),
    ):
        cr.execute(
            "SELECT res_id FROM ir_model_data WHERE module = 'mc_rov' "
            "AND name = %s AND model = %s",
            (name, model),
        )
        row = cr.fetchone()
        if not row:
            # Fallar revierte el upgrade: continuar dejaría relaciones inconsistentes.
            raise RuntimeError(f"Falta mc_rov.{name} para separar Electrónica y Software")
        ids[name] = row[0]

    # Sin subtipo no se puede inferir software; los demás componentes quedan intactos.
    for table in ("mc_rov_revision_hallazgo", "mc_rov_linea_falla"):
        cr.execute(
            f"UPDATE {table} SET componente_id = %s "
            "WHERE componente_id = %s AND subtipo_id = %s",
            (ids["comp_software"], ids["comp_electronica"], ids["sub_elec_parametros"]),
        )
        _logger.info(
            "Separación Electrónica/Software: %s filas reclasificadas en %s", cr.rowcount, table
        )
