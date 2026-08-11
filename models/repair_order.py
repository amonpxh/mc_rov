from odoo import api, models, fields
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    """Extensión de repair.order para gestión de ROVs.

    Agrega campos específicos del flujo de reparación de Marine Connection:
    tipo de intervención, ítems adicionales del sistema, registro de la falla
    reportada por el cliente, detalle de trabajos realizados y resultado final.
    """

    _inherit = "repair.order"

    # Clasifica la intervención para efectos de reportes y estadísticas.
    # Es Many2many y no Selection porque una misma visita al taller puede ser varias
    # cosas: el equipo entra a mantención y de paso se le repara algo. La relación se
    # nombra explícitamente para que la migración 19.0.4.0.0 pueda escribir en ella.
    tipo_intervencion_ids = fields.Many2many(
        "mc.rov.tipo.intervencion",
        relation="mc_rov_repair_order_tipo_rel",
        column1="repair_order_id",
        column2="tipo_id",
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
    # Almacenado porque es columna de la lista de órdenes: sin store la columna se ve
    # pero no se puede ordenar, filtrar ni agrupar, que es justo lo que se le pide a un
    # total de horas. La columna es nueva, así que el ORM la calcula sola al crearla y
    # no hace falta migración.
    mc_total_horas = fields.Float(
        string="Total HH.",
        compute="_compute_mc_total_horas",
        store=True,
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

    fecha_entrega_real = fields.Date(
        string="Fecha de entrega real",
        help="Se completa sola con la fecha de cierre si queda vacía. Corríjala si la "
        "entrega al cliente ocurrió otro día.",
    )
    observaciones_salida = fields.Text(string="Observaciones de salida")

    # --- Propiedad del equipo ---

    mc_propietario_lot_id = fields.Many2one(
        "res.partner",
        string="Propietario registrado",
        related="lot_id.mc_propietario_id",
        readonly=True,
    )

    mc_propietario_difiere = fields.Boolean(
        string="El propietario no coincide",
        compute="_compute_mc_propietario_difiere",
        help="Se enciende cuando el cliente de la orden no es el propietario que tiene "
        "registrado el equipo. Casi siempre significa que el ROV se revendió.",
    )

    @api.depends("lot_id", "partner_id", "mc_propietario_lot_id")
    def _compute_mc_propietario_difiere(self):
        """Solo compara cuando hay las dos puntas y el equipo es un ROV.

        En los lotes de componentes el propietario es siempre la empresa y la
        comparación daría alerta en todas las órdenes.
        """
        for order in self:
            order.mc_propietario_difiere = bool(
                order.lot_id.es_un_rov
                and order.partner_id
                and order.mc_propietario_lot_id
                and order.partner_id != order.mc_propietario_lot_id
            )

    @api.onchange("lot_id")
    def _onchange_lot_id_propone_propietario(self):
        """Propone como cliente al propietario registrado del equipo.

        Propuesta y no imposición: quien paga la orden no siempre es el dueño. Puede ser
        un seguro, un distribuidor que trae el equipo de un tercero, o el comprador de un
        ROV de segunda mano. Por eso solo rellena el campo vacío y nunca pisa lo que el
        técnico ya eligió.
        """
        for order in self:
            propietario = order.lot_id.mc_propietario_id
            if propietario and order.lot_id.es_un_rov and not order.partner_id:
                order.partner_id = propietario

    def action_actualizar_propietario_lote(self):
        """Traspasa el equipo al cliente de esta orden.

        Es la vía por la que el sistema se entera de que un ROV se revendió: nadie nos
        avisa de la venta entre terceros, pero el equipo vuelve al taller a nombre de
        otro. El contexto deja esta orden anotada en el historial como el origen del
        traspaso.

        No devuelve acción a propósito: al recargarse el formulario desaparece el aviso,
        que es la confirmación de que el cambio quedó hecho.
        """
        self.ensure_one()
        self.lot_id.with_context(mc_rov_repair_origen=self.id).write(
            {"mc_propietario_id": self.partner_id.id}
        )

    def _validar_tipo_intervencion(self):
        """Impide cerrar una orden que no dice qué tipo de trabajo fue.

        Sin tipo, la orden es invisible para todo lo que se calcula a partir de ella: no
        cuenta como mantención ni como reparación, no reinicia el ciclo del equipo, no
        suma a los contadores y no aparece en ultima_mantencion ni ultima_reparacion. Y
        nada avisa — es la misma falla silenciosa que tenía fecha_entrega_real, con el
        mismo síntoma diferido: meses después el equipo sigue apareciendo vencido.
        """
        sin_tipo = self.filtered(lambda order: not order.tipo_intervencion_ids)
        if not sin_tipo:
            return

        # display_name y no name: name puede venir vacío y romper el join.
        nombres = ", ".join(sin_tipo.mapped("display_name"))
        raise UserError(
            f"Indique el tipo de intervención antes de cerrar: {nombres}.\n\n"
            "Sin tipo, el trabajo no cuenta como mantención ni como reparación: no "
            "reinicia el ciclo de mantención del equipo ni aparece en su historial."
        )

    def write(self, vals):
        """Valida el cierre y sella la fecha de entrega si nadie la escribió.

        La validación va **antes** del super() para que el estado no llegue a
        escribirse. Y cubre solo la transición a done, no un @api.constrains, para no
        bloquear la edición de órdenes anteriores a la regla.

        El sellado va después, y por la razón contraria: no debe pisar una fecha que
        venga en el mismo vals.

        ultima_mantencion y ultima_reparacion en stock.lot dependen de esa fecha. Que
        quedara vacía significaba que el trabajo no contaba y el ciclo del equipo no se
        reiniciaba, sin ninguna advertencia: el técnico cerraba la orden y el número de
        serie seguía apareciendo vencido para siempre.

        Solo cubre write y no create: una orden nacida ya cerrada viene de una
        importación de datos históricos, y ahí estamparle la fecha de hoy inventaría un
        dato peor que dejarlo vacío. Quien importe debe traer su propia fecha.
        """
        if vals.get("state") == "done":
            self._validar_tipo_intervencion()

        res = super().write(vals)

        if vals.get("state") == "done":
            sin_fecha = self.filtered(lambda order: not order.fecha_entrega_real)
            if sin_fecha:
                sin_fecha.fecha_entrega_real = fields.Date.context_today(self)

        return res
