from lxml import etree

from odoo.exceptions import AccessError
from odoo.tests.common import new_test_user
from odoo.tools.safe_eval import safe_eval

from .test_mc_rov_revision import RevisionCommon


class TestFichaNavegacion(RevisionCommon):
    """Retomar y consultar evidencia no crea emisiones ni cambia su selección."""

    def _ficha(self, **vals):
        return self.env["mc.rov.ficha.equipo.nuevo"].create(
            {"name": "QA-NAVEGACION", "lot_id": self.lot.id, **vals}
        )

    def _accion(self, ficha, metodo):
        accion = getattr(ficha, metodo, None)
        self.assertTrue(callable(accion), f"Falta el acceso FEN: {metodo}")
        return accion()

    def test_retomar_abre_la_ficha_elegida_sin_crear_otra(self):
        modelo = self.env["mc.rov.ficha.equipo.nuevo"]
        for estado in ("borrador", "emitida"):
            ficha = self._ficha(estado=estado)
            self._ficha()
            antes = ficha.read()
            cantidad = modelo.search_count([])
            accion = self._accion(ficha, "action_abrir")
            self.assertEqual(accion["type"], "ir.actions.act_window")
            self.assertEqual(accion["res_model"], "mc.rov.ficha.equipo.nuevo")
            self.assertEqual(accion["res_id"], ficha.id)
            self.assertEqual(accion["view_mode"], "form")
            self.assertEqual(accion["target"], "current")
            self.assertEqual(modelo.search_count([]), cantidad)
            self.assertEqual(ficha.read(), antes)

    def test_evidencia_abre_seleccion_guardada_y_omite_referencias_vacias(self):
        ficha = self._ficha()
        self.assertFalse(self._accion(ficha, "action_abrir_rendimiento"))
        self.assertFalse(self._accion(ficha, "action_abrir_terreno"))
        rnd = self._revision(tipo="rendimiento", fecha="2026-10-01")
        trn = self._revision(tipo="terreno", fecha="2026-10-01")
        ficha.write({"rnd_id": rnd.id, "trn_id": trn.id})
        self._revision(tipo="rendimiento", fecha="2026-10-07")
        self._revision(tipo="terreno", fecha="2026-10-07")
        for registro in (ficha, self._ficha(rnd_id=rnd.id, trn_id=trn.id, estado="emitida")):
            antes = registro.read()
            for metodo, modelo, destino in (
                ("action_abrir_equipo", "stock.lot", self.lot.id),
                ("action_abrir_rendimiento", "mc.rov.revision", rnd.id),
                ("action_abrir_terreno", "mc.rov.revision", trn.id),
            ):
                accion = self._accion(registro, metodo)
                self.assertEqual(accion["res_model"], modelo)
                self.assertEqual(accion["res_id"], destino)
                self.assertEqual(accion["target"], "current")
            self.assertEqual(registro.read(), antes)

    def test_conexiones_respetan_permisos_de_ficha_y_destinos(self):
        usuario = new_test_user(self.env, login="fen_navegacion", groups="stock.group_stock_user")
        rnd = self._revision(tipo="rendimiento")
        trn = self._revision(tipo="terreno")
        ficha = self._ficha(rnd_id=rnd.id, trn_id=trn.id).with_user(usuario)
        for modelo, destino, metodo in (
            ("mc.rov.ficha.equipo.nuevo", ficha.id, "action_abrir"),
            ("stock.lot", self.lot.id, "action_abrir_equipo"),
            ("mc.rov.revision", rnd.id, "action_abrir_rendimiento"),
            ("mc.rov.revision", trn.id, "action_abrir_terreno"),
        ):
            self.assertEqual(self._accion(ficha, metodo)["res_id"], destino)
            regla = self.env["ir.rule"].create(
                {
                    "name": "Destino FEN no accesible",
                    "model_id": self.env["ir.model"]._get_id(modelo),
                    "domain_force": str([("id", "!=", destino)]),
                }
            )
            with self.assertRaises(AccessError):
                self._accion(ficha, metodo)
            if modelo == "mc.rov.ficha.equipo.nuevo":
                with self.assertRaises(AccessError):
                    self._accion(ficha, "action_abrir_equipo")
            regla.unlink()

    def test_vistas_ofrecen_accesos_segun_estado_y_referencia(self):
        vista = self.env["stock.lot"].get_view(
            view_id=self.env.ref("stock.view_production_lot_form").id, view_type="form"
        )
        form = etree.fromstring(vista["arch"])
        botones = form.xpath(
            "//field[@name='ficha_equipo_nuevo_ids']/list/button[@name='action_abrir']"
        )
        self.assertTrue(botones, "Falta Abrir/Retomar en las FEN del equipo")
        for estado, etiqueta in (("borrador", "Retomar"), ("emitida", "Abrir")):
            visibles = [
                b
                for b in botones
                if not safe_eval(b.get("invisible", "False"), {"estado": estado})
            ]
            self.assertEqual([b.get("string") for b in visibles], [etiqueta])
            self.assertEqual(visibles[0].get("type"), "object")
        vista = self.env["mc.rov.ficha.equipo.nuevo"].get_view(
            view_id=self.env.ref("mc_rov.view_ficha_equipo_nuevo_form").id, view_type="form"
        )
        form = etree.fromstring(vista["arch"])
        for metodo, campo in (
            ("action_abrir_equipo", "lot_id"),
            ("action_abrir_rendimiento", "rnd_id"),
            ("action_abrir_terreno", "trn_id"),
        ):
            boton = form.xpath(f"//div[@name='button_box']/button[@name='{metodo}']")
            self.assertEqual(len(boton), 1)
            self.assertEqual(boton[0].get("type"), "object")
            self.assertTrue(safe_eval(boton[0].get("invisible"), {campo: False}))
            self.assertFalse(safe_eval(boton[0].get("invisible"), {campo: 1}))
