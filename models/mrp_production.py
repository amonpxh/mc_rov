from collections import defaultdict

from odoo import api, fields, models
from odoo.tools import is_html_empty


class MrpProduction(models.Model):
    """La orden de fabricación es donde las lecciones tienen que aparecer solas.

    Éste es el riesgo del cementerio, localizado: *un registro de lecciones que nadie lee
    mientras arma el equipo es un cementerio*, y es peor que el riesgo habitual porque
    esto sí se va a llenar —escribir la lección es satisfactorio— y no se va a leer.

    Guardarlas en la ficha del producto no basta: el que arma un ROV no está mirando el
    producto, está mirando la orden. Y `quality_alert_ids`, que ya viene de fábrica, no
    sirve para esto — son las alertas *de esta orden*, no las lecciones históricas del
    modelo, o sea justo lo contrario de lo que hace falta.
    Ver `docs/designs/fabricacion.md` § 6.1.1.
    """

    _inherit = "mrp.production"

    mc_leccion_ids = fields.Many2many(
        "quality.alert",
        string="Lecciones de este modelo",
        compute="_compute_mc_leccion_ids",
    )
    mc_leccion_count = fields.Integer(compute="_compute_mc_leccion_ids")

    @api.depends("product_id")
    def _compute_mc_leccion_ids(self):
        """Las alertas cerradas y con acción preventiva escrita de este mismo modelo.

        **El alcance es una decisión, no un filtro de conveniencia.** Todas las alertas
        del modelo serían ruido: incluirían las que siguen abiertas, sin conclusión, y las
        que se cerraron arreglando un equipo sin cambiar nada. Las que produjeron una
        acción preventiva son exactamente las lecciones.

        Entran también las que nacieron en una orden de reparación, y eso no es un efecto
        colateral: una línea de trabajo con origen «diseño» o «manufactura propia» es un
        patrón de fabricación descubierto tarde, y éste es el canal por el que vuelve
        (§ 6.3). Fabricación no necesita detectar sus propios patrones porque reparación
        se los detecta.

        Se excluyen las de la propia orden: lo que se busca es lo aprendido *antes*, y una
        lección que salió de este mismo armado ya la conoce quien está mirando la pantalla.
        """
        # Una sola consulta para todo el conjunto: este compute no está almacenado y se
        # evalúa por registro, así que una búsqueda por orden convertiría cualquier lista
        # en una tormenta de queries.
        plantillas = self.product_id.product_tmpl_id
        candidatas = self.env["quality.alert"]
        if plantillas:
            candidatas = candidatas.search(
                [
                    ("product_tmpl_id", "in", plantillas.ids),
                    ("stage_id.done", "=", True),
                ]
            )

        por_plantilla = defaultdict(lambda: self.env["quality.alert"])
        for alerta in candidatas:
            # `action_preventive` es HTML: vacío de verdad y "<p><br></p>" se ven igual en
            # pantalla, y solo el segundo pasa un `!= False` en el dominio. Por eso el
            # filtro es en Python y no en la búsqueda.
            if is_html_empty(alerta.action_preventive):
                continue
            por_plantilla[alerta.product_tmpl_id.id] |= alerta

        for produccion in self:
            # `orden=produccion` fija el valor en la lambda. Sin eso las tres capturan la
            # misma variable del bucle y todas terminan comparando contra la última orden.
            lecciones = por_plantilla[produccion.product_id.product_tmpl_id.id].filtered(
                lambda alerta, orden=produccion: alerta.production_id != orden
            )
            produccion.mc_leccion_ids = lecciones
            produccion.mc_leccion_count = len(lecciones)

    def button_mark_done(self):
        res = super().button_mark_done()
        self.filtered(lambda produccion: produccion.state == "done")._mc_sellar_alcance()
        return res

    def _mc_sellar_alcance(self):
        """Escribe en las alertas de la orden el número de serie que acaba de nacer.

        `lot_ids` es el alcance del daño —«cambiamos el o-ring» es la lección, «estas 7
        unidades llevan el viejo» es la acción— y en el experimento del 2026-08-18 quedó
        vacío: cuando se creó la alerta, la orden todavía no tenía número de serie. Por
        eso esto ocurre al terminar la orden y no al crear la alerta (§ 6.1.5).

        Se engancha en `button_mark_done` y no en `write` porque `state` es un computado
        almacenado: nadie le escribe 'done' directamente y un override de `write` no se
        enteraría nunca. Si el super devuelve un asistente —retropedido, producción
        inmediata— la orden todavía no está terminada y esto no hace nada; el asistente
        vuelve a llamar a `button_mark_done` al confirmar, y ahí sí.

        Solo se tocan las alertas sin alcance. Una que ya nombra unidades fue acotada a
        mano, y ese juicio manda sobre el automatismo.

        El campo es `lot_producing_ids` y es Many2many: en Odoo 19 una orden puede producir
        varias series. Para un ROV normalmente es una sola, pero se agregan todas — el
        alcance del daño es «qué unidades salieron de este armado», no «la primera».
        """
        for produccion in self:
            series = produccion.lot_producing_ids
            if not series:
                continue
            sin_alcance = produccion.quality_alert_ids.filtered(lambda alerta: not alerta.lot_ids)
            if sin_alcance:
                sin_alcance.write({"lot_ids": [(4, serie.id) for serie in series]})
