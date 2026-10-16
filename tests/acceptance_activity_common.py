from odoo import Command
from odoo.tests.common import new_test_user

from .manufacturing_activity_common import ManufacturingActivityCommon


class AcceptanceActivityCommon(ManufacturingActivityCommon):
    """Escenarios nativos de equipos fabricados, sin crear pruebas técnicas ficticias."""

    _acceptance_serial_number = 0

    def _acceptance_policy(self, **values):
        user = new_test_user(
            self.env,
            login="qa_acceptance_generation_taller",
            groups="stock.group_stock_user,mrp.group_mrp_user",
        )
        calendar = self.env["resource.calendar"].create(
            {
                "name": "QA aceptación laboral",
                "tz": "America/Santiago",
                "company_id": self.env.company.id,
                "attendance_ids": [
                    Command.clear(),
                    *[
                        Command.create(
                            {
                                "name": "QA jornada",
                                "dayofweek": str(day),
                                "hour_from": 8,
                                "hour_to": 17,
                                "day_period": "morning",
                            }
                        )
                        for day in range(5)
                    ],
                ],
            }
        )
        model = self.env["mc.rov.acceptance.activity.policy"]
        data = {
            "enabled": True,
            "user_id": user.id,
            "employee_id": False,
            "calendar_id": calendar.id,
            **values,
        }
        policy = model.search([("company_id", "=", self.env.company.id)], limit=1)
        if policy:
            policy.write(data)
            return policy
        return model.create({"company_id": self.env.company.id, **data})

    def _serials(self, quantity=1):
        first = getattr(self, "_acceptance_serial_number", 0)
        self._acceptance_serial_number = first + quantity
        return self.env["stock.lot"].create(
            [
                {
                    "name": f"QA-ACE-{first + number + 1}",
                    "product_id": self.product.id,
                    "company_id": self.env.company.id,
                }
                for number in range(quantity)
            ]
        )

    def _finish_acceptance_production(self, production, lots=None, **context):
        selected = self._serials() if lots is None else lots
        production.write(
            {"lot_producing_ids": [Command.set(selected.ids)], "qty_producing": len(selected) or 1}
        )
        return production.with_context(skip_redirection=True, **context).button_mark_done()

    def _finished_production(self, quantity=1):
        production = self._production(product_qty=quantity)
        production.action_confirm()
        self._finish_acceptance_production(production, self._serials(quantity))
        return production

    def _acceptance_activities(self, lot):
        types = self.env["mail.activity.type"]
        for suffix in ("performance", "field", "rejection_performance", "rejection_field", "fen"):
            types |= (
                self.env.ref("mc_rov.activity_type_acceptance_" + suffix, raise_if_not_found=False)
                or self.env["mail.activity.type"]
            )
        return self.env["mail.activity"].search(
            [
                ("res_model", "=", "stock.lot"),
                ("res_id", "in", lot.ids),
                ("activity_type_id", "in", types.ids),
            ]
        )
