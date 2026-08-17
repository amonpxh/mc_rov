from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class DiagnosticoCommon(TransactionCase):
    """Fixtures del diagnóstico de fallas. No declara tests."""

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

    def _revision_en_borrador(self, nombre):
        """Una revisión sin confirmar colgada de la orden."""
        lot = self.env["stock.lot"].create({"name": nombre, "product_id": self.product.id})
        revision = self.env["mc.rov.revision"].create({"lot_id": lot.id, "tipo": "reparacion"})
        self.order.revision_ids = [(6, 0, revision.ids)]
        return revision


@tagged("post_install", "-at_install")
class TestRecepcion(DiagnosticoCommon):
    """Lo que el cliente dice, separado de lo que el taller comprueba.

    Lo que estos tests protegen no son los campos —eso lo hace el ORM— sino la decisión que
    se puede revertir sin darse cuenta: que el síntoma (lo que vio) y la sospecha (lo que
    deduce) son dos cosas distintas, porque el análisis de cuánto le achunta el cliente solo
    tiene sentido sobre las adivinanzas.
    """

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


@tagged("post_install", "-at_install")
class TestCierreDeOrden(DiagnosticoCommon):
    """Qué se exige para cerrar, y por qué justo eso y no más.

    Las tres validaciones del cierre —tipo de intervención, origen y repuesto— comparten un
    criterio: bloquean cuando el vacío sería indistinguible de un dato, y solo entonces. Lo
    que no bloquea, se muestra.
    """

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

    # --- El repuesto que no se registró ---

    def test_un_cambio_sin_repuesto_no_deja_cerrar(self):
        """Un «Cambio completo» sin línea de producto es una pieza que se cambió y no se anotó.

        Lo que se pierde no es papeleo: es el vínculo con el lote del repuesto, y con él la
        posibilidad de saber después qué componente falla más seguido o cuánto dura.
        """
        self._linea(
            accion_id=self.env.ref("mc_rov.accion_cambio_completo").id,
            origen="desgaste",
        )

        with self.assertRaises(UserError):
            self._cerrar()

    def test_una_accion_que_no_consume_repuesto_cierra_sin_el(self):
        """Reparar, soldar o calibrar arreglan lo que ya está: no hay pieza que registrar."""
        self._linea(accion_id=self.accion.id, origen="desgaste")

        self._cerrar()

        self.assertEqual(self.order.state, "done")

    def test_que_acciones_exigen_repuesto_sale_del_catalogo(self):
        """La regla se lee de la casilla, nunca de comparar el nombre de la acción.

        El catálogo es configurable: si mañana agregan «Reemplazo de sello», tienen que poder
        marcarla desde Configuración sin que nadie toque el código.
        """
        self.assertTrue(self.env.ref("mc_rov.accion_cambio_completo").consume_repuesto)
        self.assertTrue(self.env.ref("mc_rov.accion_cambio_componente").consume_repuesto)
        for xml_id in ("mc_rov.accion_limpieza", "mc_rov.accion_calibracion"):
            self.assertFalse(self.env.ref(xml_id).consume_repuesto)

    # --- La revisión a medio llenar se muestra, no bloquea ---

    def test_la_orden_se_cierra_con_la_revision_en_borrador(self):
        """Se evaluó bloquear y se descartó: la revisión se crea sola en toda orden de ROV.

        Exigir confirmarla obligaría a recorrer los veinte chequeos aunque el equipo haya
        entrado a cambiar un conector — y cuando responder cuesta, se marca «No aplica» en
        cadena para pasar el trámite, que envenena el dato mucho más que un borrador.
        """
        revision = self._revision_en_borrador("SN-BORRADOR")

        self._cerrar()

        self.assertEqual(revision.estado, "borrador")
        self.assertEqual(self.order.state, "done")

    def test_la_revision_en_borrador_enciende_el_indicador(self):
        """Es lo que hace visible lo que no se bloquea: sin señal, el borrador no lo ve nadie.

        Almacenado porque es criterio de un filtro de la lista, y un campo sin store no se
        puede filtrar.
        """
        self._revision_en_borrador("SN-SENAL")

        self.assertTrue(self.order.mc_revision_pendiente)
        self.assertIn(
            self.order,
            self.env["repair.order"].search([("mc_revision_pendiente", "=", True)]),
        )

    def test_confirmar_la_revision_apaga_el_indicador(self):
        """Es lo que hace que este filtro sí pueda llegar a cero, a diferencia del de síntomas.

        Una orden cerrada hace un año no se puede completar —el cliente ya no está— pero una
        revisión se confirma cualquier día. Un filtro que nunca llega a cero se deja de mirar.
        """
        revision = self._revision_en_borrador("SN-APAGA")
        self.assertTrue(self.order.mc_revision_pendiente)

        revision.estado = "confirmado"

        self.assertFalse(self.order.mc_revision_pendiente)
