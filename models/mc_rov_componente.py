from odoo import models, fields


class McRovComponente(models.Model):
    """Catálogo maestro de componentes ROV.

    Agrupa los componentes físicos y de software que pueden fallar o
    intervenirse en una orden de reparación (motor, umbilical, cámara, etc.).
    Cada componente puede tener uno o varios subtipos para mayor precisión
    en el registro de trabajos realizados.
    """

    _name = "mc.rov.componente"
    _description = "Componente ROV"
    _order = "name"

    name = fields.Char(string="Componente", required=True)
    # Subtipos gestionados desde el formulario del componente (inline)
    subtipo_ids = fields.One2many("mc.rov.subtipo", "componente_id", string="Subtipos")
    active = fields.Boolean(default=True)


class McRovSubtipo(models.Model):
    """Subtipo de un componente ROV.

    Permite detallar qué parte específica del componente fue intervenida.
    Por ejemplo, dentro de 'Motor' puede ser 'Rotor', 'Hélice' o 'ESC'.
    El dominio en mc.rov.linea.falla filtra los subtipos según el componente
    seleccionado en cada línea.
    """

    _name = "mc.rov.subtipo"
    _description = "Subtipo de componente ROV"
    _order = "componente_id, name"

    name = fields.Char(string="Subtipo", required=True)
    componente_id = fields.Many2one(
        "mc.rov.componente",
        string="Componente",
        required=True,
        ondelete="cascade",
    )
    active = fields.Boolean(default=True)


class McRovAccion(models.Model):
    """Catálogo de acciones realizadas en intervenciones ROV.

    Lista configurable de acciones estándar que el técnico puede seleccionar
    al registrar cada línea de trabajo (reparación, limpieza, calibración, etc.).
    Se gestiona desde Reparaciones > Configuración, igual que los componentes.
    """

    _name = "mc.rov.accion"
    _description = "Acción en intervención ROV"
    _order = "name"

    name = fields.Char(string="Acción", required=True)
    active = fields.Boolean(default=True)


class McRovLineaFalla(models.Model):
    """Línea de trabajo registrada en una orden de reparación.

    Cada línea describe una intervención específica: qué componente se trató,
    qué subtipo exacto, qué acción se tomó, la fecha, las horas invertidas y
    un detalle libre. Una orden puede tener múltiples líneas.
    """

    _name = "mc.rov.linea.falla"
    _description = "Línea de falla en orden de reparación"
    # El id desempata: todas las líneas nacen en sequence = 10 y solo se separan si
    # alguien las arrastra. Sin el desempate, el orden entre ellas lo decide PostgreSQL
    # y las filas se rebarajan solas entre una lectura y la siguiente.
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    repair_id = fields.Many2one(
        "repair.order",
        string="Orden de reparación",
        required=True,
        ondelete="cascade",
    )
    componente_id = fields.Many2one("mc.rov.componente", string="Componente", required=True)
    # El dominio se evalúa por fila en el one2many editable (soportado desde Odoo 17+)
    subtipo_id = fields.Many2one(
        "mc.rov.subtipo",
        string="Subtipo",
        domain="[('componente_id', '=', componente_id)]",
    )
    accion_id = fields.Many2one(
        "mc.rov.accion",
        string="Acción",
        required=True,
        ondelete="restrict",
    )
    # Por defecto hoy: la línea se registra el día en que se hace el trabajo, y sin
    # default quedaba vacía casi siempre. Una fecha corregible sirve más que un campo en
    # blanco, porque de ella depende poder situar cada trabajo en el tiempo.
    fecha = fields.Date(string="Fecha", default=fields.Date.context_today)
    horas = fields.Float(string="HH.", digits=(5, 1))
    detalle = fields.Text(string="Detalle")
