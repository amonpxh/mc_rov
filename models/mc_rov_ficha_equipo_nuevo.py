"""Documento de aceptación de un equipo nuevo, respaldado por pruebas independientes."""

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from .mc_rov_revision import _logo_blanco_ficha_uri


# Solo orden de presentación. Las secciones y sus chequeos siguen viniendo del catálogo.
FEN_ORDEN_SECCIONES = (
    "energia",
    "presion",
    "leak",
    "video",
    "comunicacion",
    "navegacion",
    "accesorios",
    "luces",
)


class McRovFichaEquipoNuevo(models.Model):
    """Ancla el equipo y las dos pruebas elegidas a un PDF inmutable al emitirlo.

    Los valores técnicos no se duplican en columnas: las revisiones conservan su propio
    historial y el PDF guardado congela exactamente lo entregado al cliente.
    """

    _name = "mc.rov.ficha.equipo.nuevo"
    _description = "Ficha de equipo nuevo"
    _order = "fecha_emision desc, id desc"

    name = fields.Char(string="Ficha", required=True, readonly=True, copy=False, default="/")
    lot_id = fields.Many2one(
        "stock.lot", string="Número de serie", required=True, index=True, ondelete="restrict"
    )
    rnd_id = fields.Many2one(
        "mc.rov.revision", string="Prueba de rendimiento", ondelete="restrict"
    )
    trn_id = fields.Many2one("mc.rov.revision", string="Prueba en terreno", ondelete="restrict")
    fecha_emision = fields.Date(
        string="Fecha de emisión", required=True, default=fields.Date.context_today
    )
    responsable_id = fields.Many2one("hr.employee", string="Responsable", ondelete="restrict")
    cliente_nombre = fields.Char(string="Cliente", readonly=True, copy=False)
    observacion = fields.Text(string="Observaciones y aceptación")
    estado = fields.Selection(
        [("borrador", "Borrador"), ("emitida", "Emitida")],
        string="Estado",
        required=True,
        default="borrador",
        copy=False,
    )
    pdf_attachment_id = fields.Many2one(
        "ir.attachment", string="PDF emitido", readonly=True, copy=False, ondelete="restrict"
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Numera cada emisión independientemente de RND y TRN."""
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("mc.rov.ficha.equipo.nuevo")
            if not vals.get("cliente_nombre") and vals.get("lot_id"):
                lot = self.env["stock.lot"].browse(vals["lot_id"])
                vals["cliente_nombre"] = lot.mc_propietario_id.display_name or ""
        return super().create(vals_list)

    @api.constrains("lot_id", "rnd_id", "trn_id")
    def _check_pruebas_del_equipo(self):
        """Una revisión de otro equipo o de una reparación no respalda esta ficha."""
        for ficha in self:
            for revision, tipo in ((ficha.rnd_id, "rendimiento"), (ficha.trn_id, "terreno")):
                if revision and (
                    revision.tipo != tipo or revision.lot_id != ficha.lot_id or revision.repair_id
                ):
                    raise ValidationError(
                        "Seleccione pruebas de rendimiento y terreno de este equipo, "
                        "sin orden de reparación."
                    )

    def write(self, vals):
        """La copia emitida no cambia si después se editan el lote o las pruebas."""
        protegidos = {
            "lot_id",
            "rnd_id",
            "trn_id",
            "fecha_emision",
            "responsable_id",
            "cliente_nombre",
            "observacion",
            "estado",
        }
        if protegidos.intersection(vals) and any(f.estado == "emitida" for f in self):
            raise UserError("La ficha emitida no se puede modificar; prepare una ficha nueva.")
        return super().write(vals)

    def _ficha_logo_blanco_uri(self):
        """Inserta el logo en el PDF sin depender del servidor HTTP."""
        return _logo_blanco_ficha_uri()

    @api.model
    def _ficha_decimal(self, valor, decimales=1):
        """Presenta magnitudes reales con el separador decimal de la ficha."""
        return f"{valor or 0:.{decimales}f}".replace(".", ",")

    @api.model
    def _ficha_etiqueta(self, registro, campo):
        """Toma el rótulo de una Selection del modelo en lugar de repetirlo en QWeb."""
        if not registro:
            return "Pendiente"
        valor = registro[campo]
        seleccion = registro._fields[campo].selection
        return dict(seleccion).get(valor, "Pendiente") if valor else "Pendiente"

    @api.model
    def _ficha_estado_css(self, revision):
        return {
            "aprobado": "ok",
            "aprobado_con_observaciones": "warning",
            "rechazado": "fail",
        }.get(revision.resultado, "pending")

    def _ficha_grupos_chequeos(self, revision):
        """Agrupa las líneas efectivas; el catálogo decide nombres y cantidades."""
        etiquetas = dict(self.env["mc.rov.chequeo"]._fields["seccion"].selection)
        por_seccion = {}
        for linea in revision.chequeo_ids:
            por_seccion.setdefault(linea.seccion, []).append(linea)
        orden = list(FEN_ORDEN_SECCIONES) + sorted(set(por_seccion) - set(FEN_ORDEN_SECCIONES))
        grupos = []
        for seccion in orden:
            lineas = por_seccion.get(seccion, [])
            if not lineas:
                continue
            estados = [linea.resultado for linea in lineas]
            if "no_ok" in estados:
                estilo = "fail"
            elif not all(estados):
                estilo = "pending"
            elif all(estado == "no_lo_tiene" for estado in estados):
                estilo = "na"
            else:
                estilo = "ok"
            grupos.append(
                {
                    "nombre": etiquetas.get(seccion, seccion).removeprefix("Prueba de "),
                    "conformes": estados.count("ok"),
                    "total": len(lineas),
                    "estilo": estilo,
                    "lineas": [
                        {
                            "nombre": linea.chequeo_id.nombre_ficha or linea.chequeo_id.name,
                            "estado": linea.resultado or "pendiente",
                        }
                        for linea in lineas
                    ],
                }
            )
        return grupos

    def action_emitir(self):
        """Guarda el PDF final; ninguna revisión posterior modifica el documento entregado."""
        self.ensure_one()
        if self.estado != "borrador":
            raise UserError("Esta ficha ya fue emitida.")
        if not self.rnd_id or not self.trn_id:
            raise UserError("Seleccione ambas pruebas de aceptación antes de emitir la ficha.")
        for revision in (self.rnd_id, self.trn_id):
            if revision.estado != "confirmado" or revision.resultado not in (
                "aprobado",
                "aprobado_con_observaciones",
            ):
                raise UserError("Ambas pruebas deben estar confirmadas y aprobadas.")
        self.write({"estado": "emitida"})
        contenido, _ = self.env["ir.actions.report"]._render_qweb_pdf(
            "mc_rov.action_report_ficha_equipo_nuevo", self.ids
        )
        nombre = f"Ficha Equipo Nuevo - {self.name.replace('/', '-')}.pdf"
        adjunto = self.env["ir.attachment"].search(
            [("res_model", "=", self._name), ("res_id", "=", self.id), ("name", "=", nombre)],
            limit=1,
        )
        if not adjunto:
            adjunto = self.env["ir.attachment"].create(
                {
                    "name": nombre,
                    "type": "binary",
                    "raw": contenido,
                    "mimetype": "application/pdf",
                    "res_model": self._name,
                    "res_id": self.id,
                }
            )
        self.pdf_attachment_id = adjunto
        return self.action_descargar()

    def action_descargar(self):
        """La versión emitida sale siempre del binario congelado."""
        self.ensure_one()
        if self.pdf_attachment_id:
            return {
                "type": "ir.actions.act_url",
                "url": f"/web/content/{self.pdf_attachment_id.id}?download=true",
                "target": "self",
            }
        return self.env.ref("mc_rov.action_report_ficha_equipo_nuevo").report_action(self)
