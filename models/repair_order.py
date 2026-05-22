from odoo import api, models, fields


class RepairOrder(models.Model):
    """Extensión de repair.order para gestión de ROVs.

    Agrega campos específicos del flujo de reparación de Marine Connection:
    tipo de intervención, ítems adicionales del sistema, registro de la falla
    reportada por el cliente, detalle de trabajos realizados y resultado final.
    """

    _inherit = "repair.order"

    # Clasifica la intervención para efectos de reportes y estadísticas
    tipo_intervencion = fields.Selection(
        [
            ("diagnostico", "Diagnóstico"),
            ("reparacion_correctiva", "Reparación correctiva"),
            ("mantencion_preventiva", "Mantención preventiva"),
            ("conversion", "Conversión / Upgrade"),
        ],
        string="Tipo de intervención",
    )

    # Ítems adicionales del sistema ROV asociados a la orden (además del número de serie)
    item_2 = fields.Char(string="Ítem 2")
    item_3 = fields.Char(string="Ítem 3")
    item_4 = fields.Char(string="Ítem 4")
    item_5 = fields.Char(string="Ítem 5")

    # Descripción literal de la falla según el cliente, sin interpretación técnica
    falla_reportada = fields.Text(string="Falla reportada por cliente")

    # Detalle técnico de los trabajos ejecutados (ver mc.rov.linea.falla)
    linea_falla_ids = fields.One2many(
        "mc.rov.linea.falla", "repair_id", string="Trabajos realizados"
    )
    mc_total_horas = fields.Float(
        string="Total HH.",
        compute="_compute_mc_total_horas",
        digits=(5, 1),
    )

    @api.depends("linea_falla_ids.horas")
    def _compute_mc_total_horas(self):
        for order in self:
            order.mc_total_horas = sum(order.linea_falla_ids.mapped("horas"))

    causa_raiz = fields.Selection(
        [
            ("mal_uso", "Mal uso"),
            ("desgaste", "Desgaste normal"),
            ("accidente", "Accidente"),
            ("falla_fabricacion", "Falla de fabricación"),
            ("corrosion", "Corrosión"),
            ("desconocida", "Desconocida"),
        ],
        string="Causa raíz",
    )

    fecha_entrega_real = fields.Date(string="Fecha de entrega real")
    observaciones_salida = fields.Text(string="Observaciones de salida")
