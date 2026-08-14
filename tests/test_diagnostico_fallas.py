from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestDiagnosticoFallas(TransactionCase):
    """Lo que 19.0.13.0.0 agrega: el síntoma reportado y la calidad de la causa.

    El diseño completo está en `docs/designs/diagnostico-de-fallas.md`. Lo que estos tests
    protegen no son los campos —eso lo hace el ORM— sino las tres decisiones que se pueden
    revertir sin darse cuenta: que el síntoma y la sospecha son cosas distintas, que el
    origen se exige al **cerrar** y no al guardar, y que «No determinado» deja cerrar.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create({"name": "ROV Test", "tracking": "serial"})
        cls.componente = cls.env.ref("mc_rov.comp_motor")
        cls.accion = cls.env.ref("mc_rov.accion_reparacion")
        cls.tipo = cls.env.ref("mc_rov.tipo_reparacion_correctiva")

    def setUp(self):
        super().setUp()
        self.order = self.env["repair.order"].create({"product_id": self.product.id})

    def _linea(self, **vals):
        return self.env["mc.rov.linea.falla"].create(
            {
                "repair_id": self.order.id,
                "componente_id": self.componente.id,
                "accion_id": self.accion.id,
                **vals,
            }
        )

    def _cerrar(self):
        """Cierra la orden con el tipo de intervención ya puesto.

        El tipo se pone siempre porque su validación corre antes que la del origen: sin él,
        cualquier test de cierre fallaría por el motivo equivocado.
        """
        self.order.tipo_intervencion_ids = [(6, 0, self.tipo.ids)]
        self.order.state = "done"

    # --- Recepción: el síntoma y la sospecha son dos campos ---

    def test_sintomas_y_sospechas_no_se_pisan(self):
        """Son dos listas distintas y el punto entero del bloque es que lo sigan siendo.

        Un ROV llega con varias quejas a la vez y el cliente puede señalar más de un
        componente; si una lista pisara a la otra se perdería justo la comparación que
        justifica el diseño —de qué sospechó contra dónde estuvo el hallazgo—.
        """
        sintomas = self.env.ref("mc_rov.sintoma_no_enciende") | self.env.ref(
            "mc_rov.sintoma_sin_imagen"
        )
        sospechas = self.env.ref("mc_rov.comp_umbilical") | self.env.ref("mc_rov.comp_camara")

        self.order.write(
            {
                "sintoma_ids": [(6, 0, sintomas.ids)],
                "componente_sospechado_ids": [(6, 0, sospechas.ids)],
            }
        )

        self.assertEqual(self.order.sintoma_ids, sintomas)
        self.assertEqual(self.order.componente_sospechado_ids, sospechas)

    def test_los_dos_campos_nacen_vacios(self):
        """Vacío es una respuesta válida: significa que el equipo llegó sin diagnóstico.

        Obligar produciría inventos —el que trae el equipo a veces no lo operó nunca— así
        que el hueco lo cubre el filtro «Sin síntoma registrado», no un required.
        """
        self.assertFalse(self.order.sintoma_ids)
        self.assertFalse(self.order.componente_sospechado_ids)

    def test_la_sospecha_usa_el_mismo_catalogo_que_el_hallazgo(self):
        """Es lo que permite preguntar «sospechó de X, ¿qué encontramos?» sin traducir.

        Si el campo tuviera catálogo propio, la comparación exigiría una tabla de
        equivalencias que nadie mantendría, y el análisis se haría leyendo párrafos.
        """
        lot = self.env["stock.lot"].create({"name": "SN-SOSPECHA", "product_id": self.product.id})
        revision = self.env["mc.rov.revision"].create({"lot_id": lot.id, "tipo": "reparacion"})
        hallazgo = self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
                "componente_id": self.componente.id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
            }
        )
        self.order.componente_sospechado_ids = [(6, 0, self.componente.ids)]

        self.assertEqual(hallazgo.componente_id, self.order.componente_sospechado_ids)

    def test_un_sintoma_archivado_desaparece_de_la_lectura_del_many2many(self):
        """Archivar no borra la fila, pero **sí la esconde de la lectura**, y hay que saberlo.

        Retirar una entrada del catálogo es desmarcar `active` y nunca borrarla: un borrado
        dejaría huérfanas las órdenes que la usaron. Pero el enlace no sobrevive a la vista:
        el ORM aplica `active_test` al leer un x2many, así que la orden pasa a informar un
        síntoma menos sin que nada avise.

        **La consecuencia es de análisis, no de pantalla.** Archivar un síntoma de uso
        corriente baja el conteo histórico de ese síntoma a cero, y la caída se ve idéntica a
        que hubiera dejado de ocurrir. Quien cuente síntomas del pasado tiene que leer con
        `active_test=False`; archivar una entrada muy usada es una decisión de datos.
        """
        sintoma = self.env.ref("mc_rov.sintoma_sonar_no_funciona")
        self.order.sintoma_ids = [(6, 0, sintoma.ids)]

        sintoma.active = False
        self.order.invalidate_recordset(["sintoma_ids"])

        # Ya no se ofrece al elegir, que es el punto de archivar.
        self.assertNotIn(sintoma, self.env["mc.rov.sintoma"].search([]))
        # Ni se ve en la orden, que es lo que el diseño daba por sentado y no es así.
        self.assertNotIn(sintoma, self.order.sintoma_ids)
        # Pero el enlace está: no se perdió nada, está escondido.
        self.assertIn(sintoma, self.order.with_context(active_test=False).sintoma_ids)

    def test_la_temporalidad_es_un_sintoma_y_no_un_campo(self):
        """El campo `momento_falla` se retiró; la temporalidad entra como etiqueta.

        Que la falla vaya y venga es algo que el cliente VIO, que es el único criterio con
        el que este diseño decide si algo es síntoma. Como campo aparte traía un valor
        por defecto que volvía imposible distinguir «no sabe» de «nadie preguntó».
        """
        self.assertNotIn("momento_falla", self.env["repair.order"]._fields)

        temporales = self.env["mc.rov.sintoma"].search([("familia", "=", "temporalidad")])

        self.assertTrue(temporales)
        self.assertIn(self.env.ref("mc_rov.sintoma_intermitente"), temporales)

    # --- El origen se exige al cerrar, no al guardar ---

    def test_una_linea_sin_origen_se_guarda(self):
        """La exigencia es del cierre, no del modelo, y la diferencia es todo el punto.

        Un `required` obligaría a contestar mientras el técnico todavía está reparando, o
        sea cuando el origen es especulación — y el resultado sería «No determinado»
        marcado para salir del paso, indistinguible de uno de verdad.
        """
        linea = self._linea()

        self.assertFalse(linea.origen)
        self.assertTrue(linea.id)

    def test_no_se_puede_cerrar_con_una_linea_sin_origen(self):
        """Es el campo que decide quién paga: bloquear el cierre formaliza lo que ya pasaba."""
        self._linea()

        with self.assertRaises(UserError):
            self._cerrar()

    def test_el_error_del_cierre_nombra_la_linea(self):
        """Sin `_compute_display_name` el error diría «mc.rov.linea.falla,42».

        El modelo no tiene campo `name`, así que Odoo cae en su nombre técnico — que para
        el técnico que intenta cerrar la orden no identifica nada.
        """
        self._linea()

        with self.assertRaises(UserError) as error:
            self._cerrar()

        self.assertIn(self.componente.name, str(error.exception))
        self.assertIn(self.accion.name, str(error.exception))
        self.assertNotIn("mc.rov.linea.falla,", str(error.exception))

    def test_se_cierra_con_origen_desconocida(self):
        """«No determinado» tiene que dejar cerrar: obligar a acusar produce acusaciones falsas.

        Además es la respuesta honesta cuando el equipo llegó destruido y no hay forma de
        reconstruir qué pasó, que es la mitad del trabajo de este taller.
        """
        self._linea(origen="desconocida")

        self._cerrar()

        self.assertEqual(self.order.state, "done")

    def test_se_cierra_sin_ninguna_linea_de_trabajo(self):
        """Una visita de diagnóstico puro no registra trabajos y no por eso está incompleta.

        La validación mira las líneas que existen; no exige que existan.
        """
        self._cerrar()

        self.assertEqual(self.order.state, "done")

    def test_el_analisis_escrito_nunca_bloquea(self):
        """Y en particular no bloquea cuando el origen apunta hacia adentro.

        Exigir justificación en «manufactura propia» le pondría fricción justo a las
        opciones incómodas, y eso empuja a marcar «desgaste normal», que es plausible
        siempre. Tiene que costar lo mismo en las seis.
        """
        self._linea(origen="falla_fabricacion")

        self._cerrar()

        self.assertEqual(self.order.state, "done")
        self.assertFalse(self.order.linea_falla_ids.analisis_causa)

    def test_el_error_nombra_solo_las_lineas_que_faltan(self):
        """Con varias líneas, el técnico tiene que saber cuál corregir sin adivinar."""
        completa = self._linea(origen="desgaste")
        otro_componente = self.env.ref("mc_rov.comp_umbilical")
        incompleta = self._linea(componente_id=otro_componente.id)

        with self.assertRaises(UserError) as error:
            self._cerrar()

        mensaje = str(error.exception)
        self.assertIn(incompleta.display_name, mensaje)
        self.assertNotIn(completa.display_name, mensaje)

    # --- La lista del cierre es la misma relación ---

    def test_la_lista_del_cierre_muestra_las_mismas_lineas(self):
        """`linea_falla_cierre_ids` no duplica datos: comparte tabla e inverso.

        Es el mismo patrón que los siete campos `chequeo_*_ids` de la revisión. Lo que
        cambia es la pantalla — el origen se contesta en la pestaña de cierre y no en la
        que se llena mientras se trabaja.
        """
        self._linea()
        self._linea()

        self.assertEqual(self.order.linea_falla_cierre_ids, self.order.linea_falla_ids)

    # --- El catálogo de síntomas ---

    def test_el_catalogo_trae_las_nueve_familias(self):
        """Una familia sin ninguna entrada sería una sección vacía en el buscador."""
        familias = set(self.env["mc.rov.sintoma"].search([]).mapped("familia"))

        self.assertEqual(len(familias), 9)

    def test_los_componentes_que_los_sintomas_nombran_existen(self):
        """El cruce «reportado vs real» se cae si el cliente no puede señalar el componente.

        Luces, manipulador y sonar aparecían como síntomas y no existían en el catálogo de
        componentes: el cliente veía «las luces no prenden» y no tenía de qué sospechar.
        """
        for xml_id in ("mc_rov.comp_luces", "mc_rov.comp_manipulador", "mc_rov.comp_sonar"):
            componente = self.env.ref(xml_id)
            self.assertTrue(componente.exists())
            # No entran a la inspección física: no se revisan buscando sellos de terceros,
            # y marcarlos agregaría tres filas a responder en cada revisión.
            self.assertFalse(componente.es_inspeccionable)
