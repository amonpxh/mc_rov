import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class QualityCheck(models.Model):
    """Extiende el chequeo de calidad para que un fallo deje registro permanente.

    El experimento sobre `odoo_staging` del 2026-08-18 encontró el hueco que hace fallar
    todo lo demás: el técnico marca Fallido, no se crea nada, nada lo detiene, arregla el
    equipo, marca Aprueba, **el fallo se sobrescribe** y la orden cierra impecable. Lo
    único que queda es una línea de chatter. Ver `docs/designs/fabricacion.md` § 2.1.

    No es un defecto de Odoo: Calidad contesta «¿esta unidad quedó buena?», y para esa
    pregunta pisar el estado es lo correcto. Lo que falta es la otra, «¿qué aprendimos
    armándola?», y esa se contesta con la alerta.
    """

    _inherit = "quality.check"

    def do_fail(self):
        """Crea la lección en el momento del fallo, que es el único momento en que existe.

        La asimetría que justifica automatizar esto y no pedirlo: marcar el chequeo como
        fallido es obligatorio para avanzar, y crear la alerta no lo pide nadie. El
        primero está en el camino, el segundo es un desvío — y los desvíos no se toman a
        las siete de la tarde con un equipo a medio armar (§ 6.1.4).

        Se engancha acá y no en `write` sobre `quality_state` porque Odoo escribe ese
        campo también al generar los chequeos de una orden, y ahí no hay fallo que
        registrar. `do_measure` de `quality_control` termina llamando a `do_pass` o a
        `do_fail` según la tolerancia, así que este único override cubre también las
        mediciones fuera de norma.
        """
        res = super().do_fail()
        self._mc_registrar_alerta_de_fallo()
        return res

    def _mc_registrar_alerta_de_fallo(self):
        """Abre la alerta del fallo, o anota el reintento en la que ya está abierta.

        **Idempotente por chequeo, y esa es la mitad del valor.** Si el técnico falla,
        ajusta y vuelve a fallar, no aparecen dos alertas: el segundo intento entra al
        chatter de la primera. Eso es lo que convierte a la alerta en el historial de
        intentos que el chequeo no guarda, porque el chequeo pisa su propio estado.

        Una alerta ya cerrada no se reabre. Si el mismo control vuelve a fallar meses
        después, eso es un hallazgo nuevo sobre una lección que ya se dio por aprendida, y
        merece su propia alerta en vez de ensuciar la anterior.

        **Solo para ROVs.** El § 6.1.4 no lo califica, pero el diseño entero habla de
        fabricación de ROVs y automatizar esto sobre toda la base tiene un costo que se
        paga en la dirección equivocada: un punto de calidad en recepción de compras
        llenaría la lista de borradores vacíos, y una lista larga de alertas que nadie
        salda destruye exactamente la señal en que se apoya el § 6.1.4 — que una alerta a
        medio llenar se lee como deuda pendiente.
        """
        categorias_rov = self._mc_categorias_rov()
        for chequeo in self.filtered(
            lambda chequeo: chequeo.product_id.categ_id in categorias_rov
        ):
            abierta = chequeo.alert_ids.filtered(lambda alerta: not alerta.stage_id.done)
            if abierta:
                abierta[0].message_post(
                    body=_(
                        "El control «%s» volvió a fallar. Sigue siendo el mismo problema: "
                        "este intento queda acá y no en una alerta nueva.",
                        chequeo.title or chequeo.name or "",
                    )
                )
                continue
            self.env["quality.alert"].create(chequeo._mc_valores_de_alerta())

    def _mc_categorias_rov(self):
        """La rama de categorías que cuenta como ROV, resuelta una vez por recordset.

        Reusa `stock.lot._get_rov_root_category()` en vez de repetir la lógica: la raíz
        sale de un parámetro de sistema con respaldo a un XML ID de importación, y tener
        dos copias de esa resolución es garantía de que un día digan cosas distintas.

        Si la raíz no resuelve, esto devuelve vacío y **no se crea ninguna alerta**. Es la
        dirección segura del fallo —callar en vez de inundar— pero es silenciosa, así que
        queda en el log. Mismo criterio que `_compute_es_un_rov`, que ante lo mismo apaga
        todos los `es_un_rov` y lo registra como ERROR.
        """
        raiz = self.env["stock.lot"]._get_rov_root_category()
        if not raiz:
            _logger.warning(
                "No se pudo resolver la categoría raíz de ROV: los chequeos de calidad "
                "fallados no abrirán su alerta automáticamente."
            )
            return self.env["product.category"]
        return self.env["product.category"].search([("id", "child_of", raiz.id)])

    def _mc_valores_de_alerta(self):
        """Los mismos campos que arma `do_alert`, más el enlace al trabajo que la originó.

        Se copia el juego de valores del botón «Crear alerta» de Odoo para que la alerta
        automática y la manual nazcan iguales. `title` se deja vacío **a propósito**: la
        alerta tiene que verse a medio llenar, porque una deuda evidente en la lista se
        salda y una lección que nunca se escribió es invisible.

        `production_id`, `repair_id` y `workorder_id` sí se agregan, y `do_alert` no los
        pone: sin ellos la alerta no aparece en la orden que la originó —los One2many de
        `quality_mrp` y `quality_repair` cuelgan justamente de esos campos— y quedaría
        solo en la app de Calidad, que es adonde nadie entra.
        """
        self.ensure_one()
        return {
            "check_id": self.id,
            "product_id": self.product_id.id,
            "product_tmpl_id": self.product_id.product_tmpl_id.id,
            # Al fallar durante el armado la orden todavía no tiene número de serie, así
            # que esto suele quedar vacío. Lo llena `mrp.production` al terminar (§ 6.1.5).
            "lot_ids": self.lot_ids.ids,
            "user_id": self.user_id.id,
            "team_id": self.team_id.id,
            "company_id": self.company_id.id,
            "production_id": self.production_id.id,
            "repair_id": self.repair_id.id,
            "workorder_id": self.workorder_id.id,
        }


class QualityAlert(models.Model):
    """La alerta de calidad es la lección aprendida, y le faltaba una sola cosa.

    No se construyó un modelo de lecciones sobre `product.template` porque `quality.alert`
    ya trae más de lo que se iba a escribir: la lección es del modelo (`product_tmpl_id`),
    el alcance del daño (`lot_ids`), la causa (`reason_id`), y sobre todo la separación
    entre lo que se corrigió (`action_corrective`) y lo que se cambia para que no vuelva a
    pasar (`action_preventive`) — que es la diferencia entre arreglar este equipo y
    cambiar cómo se arman todos. Ver `docs/designs/fabricacion.md` § 6.

    Lo único que no tenía es a dónde fue a parar la lección cuando cambió el producto.
    """

    _inherit = "quality.alert"

    # Prefijo mc_ en un campo sobre un modelo de Odoo: si algún día Enterprise agrega su
    # propio puente al ECO —que es plausible, porque el hueco es evidente— un nombre sin
    # prefijo chocaría y el módulo dejaría de instalar.
    mc_eco_id = fields.Many2one(
        "mrp.eco",
        string="Cambio de ingeniería",
        ondelete="set null",
        index="btree_not_null",
        # El ECO del mismo modelo es el caso normal; los que no declaran producto se dejan
        # elegibles porque un cambio puede alcanzar a varios modelos a la vez.
        domain="['|', ('product_tmpl_id', '=', product_tmpl_id), ('product_tmpl_id', '=', False)]",
        help="El cambio de lista de materiales que salió de esta lección.\n\n"
        "Sin este enlace, «cambiamos el BoM por esto» no queda registrado en ninguna "
        "parte: la alerta dice qué encontramos y el ECO dice qué cambiamos, pero nadie "
        "sabía que uno venía del otro. Encadenados en orden son el historial de "
        "maduración del diseño.",
    )

    def action_abrir(self):
        """Abre esta alerta en su propia pantalla, desde la lista incrustada en otra ficha.

        Misma razón y misma forma que `mc.rov.revision.action_abrir`, y el mismo motivo por
        el que no se usa `open_form_view`: el fuente de Odoo 19 lo ignora si la lista no es
        `editable` y lo evalúa a `false` en silencio.

        **Una alerta es un documento**: tiene etapa, responsable, causa, acción correctiva y
        preventiva, y su propio chatter. Mirarla en el diálogo de la pestaña del número de
        serie es un vistazo; trabajarla es otra cosa y pide su pantalla.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.display_name,
            "res_model": "quality.alert",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }
