from odoo import models, fields
from odoo.exceptions import UserError


class McRovBajaWizard(models.TransientModel):
    """Diálogo para sacar un ROV de servicio o devolverlo.

    Existe para exigir el motivo. Un "¿está seguro?" no evita el error —se contesta que
    sí sin leer— mientras que tener que escribir por qué sí lo evita: un clic distraído
    se da, un párrafo no. Y a diferencia de la confirmación, el motivo queda guardado y
    sirve después.

    Una sola entrada en el menú de acciones cubre los dos sentidos: si el equipo está
    operativo ofrece darlo de baja, y si ya está de baja muestra desde cuándo y ofrece
    reactivarlo. Se llega por el engranaje ⚙ y no por un botón en el formulario, porque
    es una acción de ciclo de vida —la familia de Duplicar y Eliminar— que no debe
    competir por atención con los campos que se miran todos los días.
    """

    _name = "mc.rov.baja.wizard"
    _description = "Dar de baja o reactivar un ROV"

    lot_id = fields.Many2one(
        "stock.lot",
        string="Número de serie",
        required=True,
        readonly=True,
        default=lambda self: self.env.context.get("active_id"),
    )

    es_un_rov = fields.Boolean(related="lot_id.es_un_rov")

    # Lo que hace de interruptor entre los dos sentidos del diálogo. Vacío = operativo.
    fecha_baja_actual = fields.Date(
        related="lot_id.mc_fecha_baja",
        string="De baja desde",
    )

    motivo_actual = fields.Text(related="lot_id.mc_motivo_baja", string="Motivo")

    fecha = fields.Date(
        string="Fecha de baja",
        required=True,
        default=fields.Date.context_today,
        help="Cuándo salió de servicio de verdad, que suele ser antes del día en que "
        "alguien lo registra en Odoo.",
    )

    motivo = fields.Text(
        string="Motivo de la baja",
        help="Qué le pasó al equipo. Queda en su ficha y en el historial de mensajes.",
    )

    def action_dar_de_baja(self):
        """Confirma la baja.

        La obligatoriedad del motivo se declara en la vista, pero se vuelve a comprobar
        acá: la vista no protege a quien llame el método por RPC, y un motivo vacío
        vacía de sentido a todo el diálogo.
        """
        self.ensure_one()
        if not self.motivo or not self.motivo.strip():
            raise UserError("Indique el motivo de la baja antes de continuar.")

        self.lot_id.dar_de_baja(self.fecha, self.motivo.strip())

    def action_reactivar(self):
        """Devuelve el equipo a servicio."""
        self.ensure_one()
        self.lot_id.reactivar()
