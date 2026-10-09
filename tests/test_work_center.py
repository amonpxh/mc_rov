from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import new_test_user
from odoo.tools.safe_eval import safe_eval

from .test_mc_rov_revision import RevisionCommon


# Una clase mantiene juntos los contratos del mismo servicio.
# pylint: disable-next=too-many-public-methods
class TestWorkCenter(RevisionCommon):
    """El centro consulta trabajo accesible y abre destinos sin cambiar evidencias."""

    def _center(self):
        self.assertTrue(
            "mc.rov.work.center" in self.env,
            "Falta el servicio de lectura mc.rov.work.center",
        )
        return self.env["mc.rov.work.center"]

    def test_entrada_rov_abre_cliente_sin_sustituir_menus_nativos(self):
        menu = self.env.ref("mc_rov.menu_mc_rov_work_center")
        root = self.env.ref("mc_rov.menu_mc_rov_root")
        action = self.env.ref("mc_rov.action_mc_rov_work_center")
        self.assertEqual(menu.parent_id, root)
        self.assertEqual(menu.action, action)
        self.assertEqual(action.tag, "mc_rov.work_center")
        groups_field = "group_ids" if "group_ids" in root._fields else "groups_id"
        self.assertIn(self.env.ref("base.group_user"), root[groups_field])

    def _ficha(self, **vals):
        return self.env["mc.rov.ficha.equipo.nuevo"].create(
            {"name": "QA-CENTRO", "lot_id": self.lot.id, **vals}
        )

    def _row_ids(self, result):
        return {row["id"] for row in result["rows"]}

    def test_responsables_de_pruebas_y_fen_son_los_empleados_guardados(self):
        center = self._center()
        cases = []
        for topic, kind, tipo in (
            ("repair", "reviews", "reparacion"),
            ("acceptance", "performance", "rendimiento"),
            ("acceptance", "field", "terreno"),
        ):
            cases.append((topic, kind, self._revision(tipo=tipo), "Técnico responsable"))
        cases.append(
            ("acceptance", "fen", self._ficha(responsable_id=self.empleado.id), "Responsable")
        )
        for topic, kind, record, label in cases:
            with self.subTest(kind=kind):
                before = record.read(["responsable_id", "write_date"])
                result = center.get_records(topic, kind, state_filter="all")
                self.assertEqual(result.get("responsible_label"), label)
                row = next(row for row in result["rows"] if row["id"] == record.id)
                self.assertEqual(row.get("responsible"), self.empleado.name)
                self.assertEqual(record.read(["responsable_id", "write_date"]), before)

    def test_responsable_de_orden_es_usuario_asignado_no_autor(self):
        user = new_test_user(self.env, login="center_order_owner", groups="stock.group_stock_user")
        order = self.env["repair.order"].create(
            {"product_id": self.product.id, "lot_id": self.lot.id, "user_id": user.id}
        )
        result = self._center().get_records("repair", "orders", state_filter="all")
        self.assertEqual(result.get("responsible_label"), "Responsable")
        row = next(row for row in result["rows"] if row["id"] == order.id)
        self.assertEqual(row.get("responsible"), user.name)
        self.assertNotEqual(order.create_uid, user)

    def test_sin_responsable_no_infiere_autor_y_equipo_no_tiene_columna(self):
        revision = self._revision(responsable_id=False)
        result = self._center().get_records("repair", "reviews", state_filter="all")
        self.assertEqual(result.get("responsible_label"), "Técnico responsable")
        row = next(row for row in result["rows"] if row["id"] == revision.id)
        self.assertFalse(row.get("responsible"))
        self.assertEqual(row.get("responsible_state"), "unassigned")
        equipment = self._center().get_records("equipment", "equipment")
        self.assertFalse(equipment.get("responsible_label"))

    def test_nombre_publico_del_tecnico_no_requiere_permisos_privados_de_rrhh(self):
        user = new_test_user(
            self.env, login="center_technician_reader", groups="stock.group_stock_user"
        )
        revision = self._revision()
        self.assertFalse(self.env["hr.employee"].with_user(user).has_access("read"))
        result = (
            self._center().with_user(user).get_records("repair", "reviews", state_filter="all")
        )
        self.assertEqual(result.get("responsible_label"), "Técnico responsable")
        row = next(row for row in result["rows"] if row["id"] == revision.id)
        self.assertEqual(row.get("responsible"), self.empleado.name)

    def test_tecnico_restringido_no_revela_nombre_ni_oculta_revision(self):
        user = new_test_user(
            self.env, login="center_technician_hidden", groups="stock.group_stock_user"
        )
        revision = self._revision()
        for model in ("hr.employee", "hr.employee.public"):
            self.env["ir.rule"].create(
                {
                    "name": "Técnico no accesible en centro",
                    "model_id": self.env["ir.model"]._get_id(model),
                    "domain_force": str([("id", "!=", self.empleado.id)]),
                }
            )
        result = (
            self._center().with_user(user).get_records("repair", "reviews", state_filter="all")
        )
        self.assertEqual(result.get("responsible_label"), "Técnico responsable")
        row = next(row for row in result["rows"] if row["id"] == revision.id)
        self.assertFalse(row.get("responsible"))
        self.assertEqual(row.get("responsible_state"), "restricted")

    def test_equipo_filtra_rov_modelo_y_serie_con_lista_del_mismo_ambito(self):
        center = self._center()
        other_category = self.env["product.category"].create({"name": "Fuera de ROV"})
        other_product = self.env["product.product"].create(
            {"name": "Componente", "tracking": "serial", "categ_id": other_category.id}
        )
        other_lot = self.env["stock.lot"].create(
            {"name": "ROV-PROT-COMPONENTE", "product_id": other_product.id}
        )
        filters = {
            "state_filter": "all",
            "query": "ROV-PROT",
            "model_id": self.product.product_tmpl_id.id,
        }
        result = center.get_records("equipment", "equipment", **filters)
        self.assertEqual(self._row_ids(result), {self.lot.id})
        self.assertNotIn(other_lot.id, self._row_ids(result))
        action = center.action_list("equipment", "equipment", **filters)
        domain = action["domain"]
        if isinstance(domain, str):
            domain = safe_eval(domain)
        self.assertEqual(result["total"], self.env[action["res_model"]].search_count(domain))

    def test_aceptacion_separa_tipos_reales_y_excluye_visitas_de_reparacion(self):
        center = self._center()
        rnd = self._revision(tipo="rendimiento")
        trn = self._revision(tipo="terreno")
        rev = self._revision(tipo="reparacion")
        order = self.env["repair.order"].create(
            {"product_id": self.product.id, "lot_id": self.lot.id}
        )
        linked = self._revision(tipo="rendimiento", repair_id=order.id)
        filters = {"state_filter": "all", "model_id": self.product.product_tmpl_id.id}
        for kind, chosen in (("performance", rnd), ("field", trn)):
            result = center.get_records("acceptance", kind, **filters)
            self.assertEqual(self._row_ids(result), {chosen.id})
            self.assertNotIn(rev.id, self._row_ids(result))
            self.assertNotIn(linked.id, self._row_ids(result))

    def test_fichas_separan_borradores_y_emitidas_sin_inventar_pendientes(self):
        center = self._center()
        draft = self._ficha()
        issued = self._ficha(estado="emitida")
        filters = {"model_id": self.product.product_tmpl_id.id}
        opened = center.get_records("acceptance", "fen", state_filter="open", **filters)
        self.assertEqual(self._row_ids(opened), {draft.id})
        all_records = center.get_records("acceptance", "fen", state_filter="all", **filters)
        self.assertEqual(self._row_ids(all_records), {draft.id, issued.id})
        self.assertEqual(all_records["total"], 2)

    def test_abrir_ficha_elegida_no_crea_ni_sustituye_su_evidencia(self):
        center = self._center()
        rnd = self._revision(tipo="rendimiento")
        trn = self._revision(tipo="terreno")
        chosen = self._ficha(rnd_id=rnd.id, trn_id=trn.id)
        self._ficha()
        self._revision(tipo="rendimiento")
        before = chosen.read(["name", "estado", "rnd_id", "trn_id", "write_date"])
        count = self.env[chosen._name].search_count([])
        action = center.action_open("acceptance", "fen", chosen.id)
        self.assertEqual(action["res_id"], chosen.id)
        self.assertEqual(action["res_model"], chosen._name)
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual(chosen.read(["name", "estado", "rnd_id", "trn_id", "write_date"]), before)
        self.assertEqual(self.env[chosen._name].search_count([]), count)

    def test_reglas_ocultan_filas_conteos_y_prohiben_abrir_id_oculta(self):
        center = self._center()
        user = new_test_user(self.env, login="work_center_stock", groups="stock.group_stock_user")
        hidden = self.env["stock.lot"].create(
            {"name": "CENTRO-OCULTO", "product_id": self.product.id}
        )
        self.env["ir.rule"].create(
            {
                "name": "Unidad oculta del centro",
                "model_id": self.env["ir.model"]._get_id("stock.lot"),
                "domain_force": str([("id", "!=", hidden.id)]),
            }
        )
        center = center.with_user(user)
        result = center.get_records(
            "equipment",
            "equipment",
            state_filter="all",
            model_id=self.product.product_tmpl_id.id,
        )
        self.assertEqual(self._row_ids(result), {self.lot.id})
        self.assertEqual(result["total"], 1)
        with self.assertRaises(AccessError):
            center.action_open("equipment", "equipment", hidden.id)
        self.assertEqual(
            center.action_open("equipment", "equipment", self.lot.id)["res_id"], self.lot.id
        )

    def test_parametros_no_admiten_modelos_arbitrarios_y_crear_prueba_elige_equipo(self):
        center = self._center()
        for topic, kind, filters in (
            ("unknown", "equipment", {}),
            ("equipment", "res.users", {}),
            ("equipment", "equipment", {"state_filter": "arbitrary"}),
            ("equipment", "equipment", {"offset": -1}),
        ):
            with self.subTest(topic=topic, kind=kind, filters=filters):
                with self.assertRaises(UserError):
                    center.get_records(topic, kind, **filters)
        count = self.env["mc.rov.revision"].search_count([])
        action = center.action_create("acceptance", "performance")
        self.assertEqual(action["res_model"], "stock.lot")
        self.assertFalse(action.get("res_id"))
        self.assertEqual(self.env["mc.rov.revision"].search_count([]), count)

    def test_tipo_sin_acl_no_revela_conteo_ni_bloquea_equipos(self):
        user = new_test_user(self.env, login="center_partial", groups="stock.group_stock_user")
        self.assertFalse(self.env["mrp.eco"].with_user(user).has_access("read"))
        center = self._center().with_user(user)
        overview = {(row["topic"], row["kind"]): row for row in center.get_overview()}
        restricted = overview[("design", "changes")]
        self.assertFalse(restricted["available"])
        self.assertNotIn("count", restricted)
        self.assertTrue(overview[("equipment", "equipment")]["available"])
        with self.assertRaises(AccessError):
            center.get_records("design", "changes")

    def test_categoria_ausente_no_se_convierte_en_catalogo_completo_o_cero(self):
        center = self._center()
        with patch.object(
            type(self.env["stock.lot"]), "_get_rov_root_category", return_value=False
        ):
            with self.assertRaisesRegex(UserError, "categoría raíz ROV"):
                center.get_overview()
            with self.assertRaises(UserError):
                center.action_list("equipment", "equipment")

    def test_compania_fuera_del_contexto_no_aparece_ni_se_abre(self):
        company = self.env["res.company"].create({"name": "Centro otra compañía"})
        other = self.env["stock.lot"].create(
            {
                "name": "CENTRO-OTRA-COMPANIA",
                "product_id": self.product.id,
                "company_id": company.id,
            }
        )
        center = self._center().with_context(allowed_company_ids=[self.env.company.id])
        result = center.get_records("equipment", "equipment", state_filter="all")
        self.assertNotIn(other.id, self._row_ids(result))
        with self.assertRaises(AccessError):
            center.action_open("equipment", "equipment", other.id)

    def test_acciones_de_revision_proponen_el_tipo_de_su_seccion(self):
        center = self._center()
        for topic, kind, expected in (
            ("repair", "reviews", "reparacion"),
            ("acceptance", "performance", "rendimiento"),
            ("acceptance", "field", "terreno"),
        ):
            action = center.action_list(topic, kind)
            self.assertEqual(action["context"].get("default_tipo"), expected)
        self.assertEqual(
            center.action_create("repair", "reviews")["context"].get("default_tipo"),
            "reparacion",
        )

    def test_documentos_de_equipo_respetan_compania_en_conteo_lista_y_apertura(self):
        company = self.env["res.company"].create({"name": "Centro documentos otra compañía"})
        lot = self.env["stock.lot"].create(
            {
                "name": "CENTRO-DOCUMENTOS-OTRA",
                "product_id": self.product.id,
                "company_id": company.id,
            }
        )
        revision = self._revision(lot_id=lot.id, tipo="reparacion")
        fen = self._ficha(lot_id=lot.id)
        center = self._center().with_context(allowed_company_ids=[self.env.company.id])
        overview = center.get_overview()
        for topic, kind, record in (("repair", "reviews", revision), ("acceptance", "fen", fen)):
            result = center.get_records(topic, kind, state_filter="all")
            self.assertNotIn(record.id, self._row_ids(result))
            action = center.action_list(topic, kind)
            self.assertNotIn(record, self.env[record._name].search(action["domain"]))
            entry = next(row for row in overview if row["topic"] == topic and row["kind"] == kind)
            self.assertEqual(entry["count"], 0)
            with self.assertRaises(AccessError):
                center.action_open(topic, kind, record.id)

    def test_equipos_filtran_estado_operativo_con_lista_equivalente(self):
        center = self._center()
        for state in ("Operativo", "En mantención", "En reparación"):
            try:
                result = center.get_records("equipment", "equipment", state_filter=state)
                action = center.action_list("equipment", "equipment", state_filter=state)
            except UserError as error:
                self.fail(f"Falta filtro de estado operativo: {error}")
            if state == "Operativo":
                self.assertIn(self.lot.id, self._row_ids(result))
            self.assertIn(("mc_estado_operativo", "=", state), action["domain"])
            self.assertEqual(result["total"], self.env["stock.lot"].search_count(action["domain"]))
            units = self.env["stock.lot"].browse(list(self._row_ids(result)))
            self.assertTrue(all(unit.mc_estado_operativo == state for unit in units))

    def test_candidatas_abren_cola_nativa_rov_sin_crear_alertas(self):
        center = self._center()
        self.assertTrue(
            hasattr(center, "action_candidates"), "Falta acceso a Candidatas a lección"
        )
        order = self.env["repair.order"].create(
            {"product_id": self.product.id, "lot_id": self.lot.id}
        )
        candidate = self.env["mc.rov.linea.falla"].create(
            {
                "repair_id": order.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "accion_id": self.env.ref("mc_rov.accion_reparacion").id,
                "origen": "diseno",
            }
        )
        outside = self.env["product.product"].create({"name": "Fuera del centro"})
        outside_order = self.env["repair.order"].create({"product_id": outside.id})
        excluded = candidate.copy({"repair_id": outside_order.id})
        count = self.env["quality.alert"].search_count([])
        action = center.action_candidates()
        self.assertEqual(action["res_model"], "mc.rov.linea.falla")
        self.assertTrue(action["context"].get("search_default_pendientes"))
        records = self.env[action["res_model"]].search(action["domain"])
        self.assertIn(candidate, records)
        self.assertNotIn(excluded, records)
        self.assertEqual(self.env["quality.alert"].search_count([]), count)

    def test_filtro_modelos_incluye_equipo_accesible_con_modelo_archivado_fuera_de_categoria_rov(
        self,
    ):
        center = self._center()
        self.assertTrue(
            hasattr(center, "get_equipment_models"),
            "Falta filtro de modelos por equipos accesibles",
        )
        product = self.env["product.product"].create(
            {"name": "QA MODELO HISTORICO", "tracking": "serial"}
        )
        lot = self.env["stock.lot"].create({"name": "QA-HISTORICO", "product_id": product.id})
        product.product_tmpl_id.write({"active": False})
        # Reproduce el estado legado observado en STAGING, sin normalizar datos reales.
        self.env["stock.lot"].flush_model(["es_un_rov"])
        self.env.cr.execute("UPDATE stock_lot SET es_un_rov = TRUE WHERE id = %s", [lot.id])
        lot.invalidate_recordset(["es_un_rov"])
        result = center.get_equipment_models(query="QA MODELO HISTORICO")
        self.assertEqual(self._row_ids(result), {product.product_tmpl_id.id})
        rows = center.get_records("equipment", "equipment", model_id=product.product_tmpl_id.id)
        self.assertIn(lot.id, self._row_ids(rows))
        self.assertFalse(product.product_tmpl_id.active)
        self.assertNotEqual(product.categ_id, self.product.categ_id)

    def test_filtro_modelos_no_revela_modelo_de_equipo_oculto(self):
        center = self._center()
        self.assertTrue(
            hasattr(center, "get_equipment_models"),
            "Falta filtro de modelos por equipos accesibles",
        )
        product = self.env["product.product"].create(
            {
                "name": "QA MODELO RESTRINGIDO",
                "tracking": "serial",
                "categ_id": self.product.categ_id.id,
            }
        )
        lot = self.env["stock.lot"].create({"name": "QA-PRIVADO", "product_id": product.id})
        user = new_test_user(self.env, login="center_model_scope", groups="stock.group_stock_user")
        self.env["ir.rule"].create(
            {
                "name": "Equipo privado del filtro",
                "model_id": self.env["ir.model"]._get_id("stock.lot"),
                "domain_force": str([("id", "!=", lot.id)]),
            }
        )
        result = center.with_user(user).get_equipment_models(query="QA MODELO RESTRINGIDO")
        self.assertFalse(result["rows"])
        self.assertEqual(result["total"], 0)
