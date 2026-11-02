from odoo import _, models
from odoo.exceptions import UserError


class AutomaticActivityCompletion(models.Model):
    """Un aviso automático pendiente solo se cierra desde su trabajo real."""

    _inherit = "mail.activity"

    def _mc_check_automatic_completion(self):
        # Estos gateways validan actividad/origen y bloquean el seguimiento en
        # el mismo orden que su flujo. El nombre o tipo del aviso no autorizan
        # ni identifican un cierre, y un contexto RPC no permite saltárselo.
        for getter in (
            self._mc_repair_runs,
            self._mc_manufacturing_runs,
            self._mc_acceptance_runs,
            self._mc_quality_runs,
            self._mc_engineering_runs,
            self._mc_inventory_runs,
        ):
            if getter().filtered(lambda run: run.outcome == "pending"):
                raise UserError(
                    _(
                        "Esta actividad corresponde a trabajo automático pendiente. "
                        "Abra la operación y complétela o cancélela desde su proceso; "
                        "el aviso se cerrará automáticamente con el resultado real."
                    )
                )

    def _action_done(self, feedback=False, attachment_ids=None):
        with self.env.cr.savepoint():
            self._mc_check_automatic_completion()
            return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

    def action_cancel(self):
        with self.env.cr.savepoint():
            # El método nativo cancela uno por uno: validar el lote completo
            # antes de retirar una actividad manual que lo acompañe.
            self._mc_check_automatic_completion()
            return super().action_cancel()

    def unlink(self):
        with self.env.cr.savepoint():
            self._mc_check_automatic_completion()
            return super().unlink()

    def write(self, values):
        if "active" in values and not values["active"]:
            with self.env.cr.savepoint():
                self._mc_check_automatic_completion()
                return super().write(values)
        return super().write(values)
