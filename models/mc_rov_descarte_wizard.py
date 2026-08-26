from odoo import models, fields, api
from odoo.exceptions import UserError


class McRovDescarteWizard(models.TransientModel):
    """Descartar candidatas a lección, con un motivo y de a varias.

    **Existe porque el descarte estaba ocupando el gesto equivocado.** Hasta 19.0.22.4.0 la
    cola era una lista editable cuya única columna escribible era «Descartado porque», así
    que hacer clic en cualquier fila —el gesto natural para leerla— metía al usuario a
    escribir un descarte. La acción principal de esa pantalla es concluir la lección, no
    tirarla; ofrecer el descarte como respuesta por omisión al clic es lo contrario de lo que
    la pantalla quiere lograr. Lo levantó Paulo el 2026-08-25.

    Ahora la cola tiene **dos botones simétricos** sobre lo seleccionado: escribir la lección
    o descartar. Los dos actúan sobre la selección, que es como se mira esa pantalla — un
    patrón se lee con varias filas a la vista, y descartarlo también.

    **Y de paso arregla algo que no se había notado:** descartar cuatro trabajos del mismo
    patrón obligaba a teclear el mismo motivo cuatro veces, una por fila. Acá se escribe una
    vez para toda la selección.

    El motivo sigue siendo obligatorio, por la razón del asistente de baja: tener que
    escribir por qué evita el descarte distraído, y encima deja un dato que sirve después.
    """

    _name = "mc.rov.descarte.wizard"
    _description = "Descartar candidatas a lección"

    linea_ids = fields.Many2many("mc.rov.linea.falla", string="Trabajos")

    # Un resumen para que la persona vea qué está descartando sin volver atrás. El asistente
    # se abre encima de la lista y tapa justamente las filas que hay que mirar.
    resumen = fields.Text(string="Se van a descartar", readonly=True)

    motivo = fields.Char(
        string="Por qué no es una lección",
        required=True,
        help="Queda guardado en cada trabajo. Sirve después para revisar qué se decidió "
        "no promover y con qué criterio.",
    )

    @api.model
    def default_get(self, fields_list):
        valores = super().default_get(fields_list)
        lineas = self.env["mc.rov.linea.falla"].browse(self.env.context.get("active_ids", []))
        if not lineas:
            raise UserError("Seleccione al menos un trabajo para descartar.")

        ya_descartadas = lineas.filtered("mc_descarte_motivo")
        if ya_descartadas:
            nombres = ", ".join(ya_descartadas.mapped("display_name"))
            raise UserError(
                "Estos trabajos ya estaban descartados:\n\n"
                f"{nombres}\n\n"
                "Quíteles la selección para continuar con el resto."
            )

        valores["linea_ids"] = lineas.ids
        valores["resumen"] = "\n".join(
            f"· {linea.repair_id.lot_id.name or linea.repair_id.display_name} — "
            f"{linea.display_name}"
            for linea in lineas
        )
        return valores

    def action_descartar(self):
        """Escribe el motivo en los trabajos seleccionados, que con eso salen de la cola.

        **Y lo dice.** Sin el aviso, las filas simplemente desaparecían de la lista y el
        usuario se quedaba sin saber si había pasado lo que quería, si se descartó de más, o
        si el sistema hizo algo por su cuenta. Le pasó a Paulo el 2026-08-26: *«ni siquiera
        recuerdo qué apreté, solo desapareció»*.

        **Una fila que se va sin decir nada se ve igual que un error**, y en una pantalla
        donde la acción principal es un juicio humano eso erosiona la confianza en las dos
        acciones, no solo en ésta.
        """
        self.ensure_one()
        self.linea_ids.write({"mc_descarte_motivo": self.motivo})

        cuantos = len(self.linea_ids)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": (
                    f"{cuantos} trabajo(s) descartados. Salen de la lista y el motivo queda "
                    "guardado en cada uno."
                ),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
