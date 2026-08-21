from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

from odoo.addons.mc_rov.models.stock_lot import ROV_CATEG_PARAM


@tagged("post_install", "-at_install")
class RevisionCommon(TransactionCase):
    """Fixtures de los tests de revision. No declara tests.

    Necesita el árbol de categorías porque la revisión lee es_un_rov del lote, y sin
    categoría ROV los lotes de prueba no lo estarían.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        categoria = cls.env["product.category"].create({"name": "ROV Test - Revisiones"})
        cls.env["ir.config_parameter"].sudo().set_param(ROV_CATEG_PARAM, str(categoria.id))

        cls.product = cls.env["product.product"].create(
            {"name": "ROV Test Revisión", "tracking": "serial", "categ_id": categoria.id}
        )
        cls.empleado = cls.env["hr.employee"].create({"name": "Técnico de Prueba"})

    def setUp(self):
        super().setUp()
        self.lot = self.env["stock.lot"].create(
            {"name": "ROV-PROT-001", "product_id": self.product.id}
        )

    def _revision(self, **vals):
        return self.env["mc.rov.revision"].create(
            {
                "lot_id": self.lot.id,
                "responsable_id": self.empleado.id,
                **vals,
            }
        )

    def _corrida_completa(self, revision, **vals):
        """Llena las condiciones de la prueba para que no impidan confirmar.

        Desde 19.0.15.0.0 la corrida no es un modelo aparte: es la propia revisión, con un
        solo umbilical. El helper conserva el nombre porque lo que hace es lo mismo — dejar
        registrada la pasada completa— y porque así los tests siguen leyéndose igual.
        """
        revision.write(
            {
                "umbilical": "equipo",
                "largo": 100.0,
                "alimentacion": "Generador",
                "tension_salida": 220,
                "funcionamiento_continuo_duracion": 1.5,
                "funcionamiento_continuo_resultado": "ok",
                **vals,
            }
        )
        return revision

    def _responder_todo(self, revision, resultado="ok"):
        """Responde el checklist. Los sellos van aparte, para poder probarlos solos."""
        revision.chequeo_ids.write({"resultado": resultado})

    def _responder_sellos(self, revision, estado="intacto"):
        revision.inspeccion_ids.write({"estado_sello": estado})

    def _chequeo_catalogo(self, **vals):
        """Un paso de testeo creado para el test.

        Desde 19.0.12.0.0 el catálogo de datos corre entero en los tres tipos de revisión,
        así que el filtro por tipo y la generación por componente ya no se pueden observar
        sobre los registros de `mc_rov_revision_data.xml`. Se prueban contra un chequeo
        propio: es el mecanismo lo que hay que cubrir, no el contenido del catálogo, que
        cambia sin desplegar.
        """
        return self.env["mc.rov.chequeo"].create(
            {
                "name": "Chequeo de prueba",
                "seccion": "otro",
                "aplica_rendimiento": False,
                "aplica_reparacion": False,
                "aplica_terreno": False,
                **vals,
            }
        )


@tagged("post_install", "-at_install")
class TestMcRovRevision(RevisionCommon):
    """Tests de la cabecera: secuencia, derivados y generación del checklist."""

    def test_el_revision_toma_su_numero_de_la_secuencia(self):
        self.assertTrue(self._revision().name.startswith("REV/"))

    def test_el_revision_deriva_el_equipo_sin_guardar_contactos_propios(self):
        """Propietario y cliente son dos cosas distintas y ninguna vive acá."""
        revision = self._revision()

        self.assertEqual(revision.product_id, self.product)
        self.assertEqual(revision.propietario_id, self.lot.mc_propietario_id)
        self.assertFalse(revision.partner_id)

    def test_una_revision_trae_su_checklist_generado(self):
        """Las líneas las pone el sistema: si las eligiera el técnico, no habría forma de
        distinguir "revisado y limpio" de "no se me ocurrió mirarlo"."""
        revision = self._revision()

        self.assertTrue(revision.chequeo_ids)

    def test_un_chequeo_que_no_aplica_al_tipo_no_se_genera(self):
        """Sin este filtro, un chequeo pensado para terreno aparecería en toda ficha de
        taller y habría que responderlo para poder confirmar."""
        solo_terreno = self._chequeo_catalogo(aplica_terreno=True)

        reparacion = self._revision(tipo="reparacion")
        terreno = self._revision(tipo="terreno")

        self.assertNotIn(solo_terreno, reparacion.chequeo_ids.mapped("chequeo_id"))
        self.assertIn(solo_terreno, terreno.chequeo_ids.mapped("chequeo_id"))

    def test_un_chequeo_por_componente_genera_una_linea_por_componente(self):
        """Y solo por los inspeccionables: sin ese filtro saldría una línea por cada entrada
        del catálogo, umbilical y sensor incluidos."""
        por_componente = self._chequeo_catalogo(aplica_reparacion=True, por_componente=True)

        revision = self._revision(tipo="reparacion")

        lineas = revision.chequeo_ids.filtered(lambda linea: linea.chequeo_id == por_componente)
        componentes = lineas.mapped("componente_id")
        self.assertTrue(componentes)
        self.assertTrue(all(componentes.mapped("es_inspeccionable")))

    def test_ningun_chequeo_del_catalogo_se_hace_por_componente(self):
        """Las marcas de plumón eran el único, y salieron de la batería en 19.0.12.0.0.

        Si vuelve a aparecer uno sin querer, cada ficha crece en cinco filas por chequeo y
        el técnico las tiene que responder todas para confirmar.
        """
        revision = self._revision(tipo="reparacion")

        self.assertFalse(revision.chequeo_ids.mapped("componente_id"))

    def test_el_checklist_sale_en_el_orden_del_catalogo_y_no_de_creacion(self):
        """Hasta `19.0.15.2.1` la línea llevaba `sequence = 10` fija, así que `_order` caía a
        `id` y la ficha se mostraba **en orden de creación**.

        Se veía en pantalla y nadie lo relacionaba con esto: un chequeo agregado al catálogo
        después quedaba último para siempre, y reordenar el catálogo no movía ni una ficha ya
        creada — que es lo que dejó sin efecto el reordenamiento de navegación de 19.0.14.2.0.

        El segundo tramo es el que importa de verdad: reordenar el catálogo tiene que
        reordenar lo que ya existe, o el arreglo solo sirve para las revisiones nuevas.
        """
        ultimo = self._chequeo_catalogo(
            aplica_reparacion=True, seccion="otro", sequence=900, name="Va al final"
        )
        primero = self._chequeo_catalogo(
            aplica_reparacion=True, seccion="otro", sequence=1, name="Va al principio"
        )

        revision = self._revision(tipo="reparacion")
        propios = revision.chequeo_otro_ids.filtered(
            lambda linea: linea.chequeo_id in primero | ultimo
        )

        self.assertEqual(propios.mapped("chequeo_id"), primero | ultimo)

        ultimo.sequence = 0
        revision.invalidate_recordset()

        reordenados = revision.chequeo_otro_ids.filtered(
            lambda linea: linea.chequeo_id in primero | ultimo
        )
        self.assertEqual(reordenados.mapped("chequeo_id"), ultimo | primero)

    def test_los_chequeos_de_software_son_solo_de_reparacion(self):
        """`19.0.15.2.0` los agrega **solo** a la batería de reparación, y eso es una decisión,
        no un olvido.

        En fabricación el software lo instala uno mismo, así que compararlo contra la ficha no
        afirma lo mismo. Y encender las tres casillas por costumbre es exactamente la omisión
        que dejó la batería de fabricación sin definir — ver `docs/pendientes.md`.

        Este test existe porque el error se ve idéntico a un descuido: alguien "completa" los
        dos registros del XML y nadie lo nota hasta que un ROV recién armado pide software que
        acaba de instalar.
        """
        software = self.env.ref("mc_rov.chequeo_software_opera") | self.env.ref(
            "mc_rov.chequeo_software_ficha"
        )

        self.assertTrue(all(software.mapped("aplica_reparacion")))
        self.assertFalse(any(software.mapped("aplica_rendimiento")))
        self.assertFalse(any(software.mapped("aplica_terreno")))

        reparacion = self._revision(tipo="reparacion").chequeo_ids.mapped("chequeo_id")
        rendimiento = self._revision(tipo="rendimiento").chequeo_ids.mapped("chequeo_id")

        self.assertFalse(software - reparacion)
        self.assertFalse(software & rendimiento)

    def test_cambiar_el_tipo_ajusta_el_checklist_sin_borrar_respuestas(self):
        """Cambiar de tipo quita las líneas que ya no corresponden, pero nunca las que
        alguien contestó: el dato ya se levantó."""
        solo_reparacion = self._chequeo_catalogo(aplica_reparacion=True)
        revision = self._revision(tipo="reparacion")

        propias = revision.chequeo_ids.filtered(lambda linea: linea.chequeo_id == solo_reparacion)
        respondida = propias[0]
        respondida.resultado = "ok"

        revision.tipo = "rendimiento"

        self.assertIn(respondida, revision.chequeo_ids)

    def test_cambiar_el_tipo_borra_lo_que_quedo_sin_responder(self):
        solo_reparacion = self._chequeo_catalogo(aplica_reparacion=True)
        revision = self._revision(tipo="reparacion")
        propias = revision.chequeo_ids.filtered(lambda linea: linea.chequeo_id == solo_reparacion)

        revision.tipo = "rendimiento"

        self.assertFalse(propias.exists())

    def test_el_boton_trae_los_chequeos_agregados_despues_de_abrir_la_ficha(self):
        """La revisión nace al confirmar la orden, o sea apenas el equipo entra al taller.

        Sin este botón, un chequeo agregado al catálogo mientras hay equipos en el taller no
        alcanza a ninguno de ellos: solo a los que lleguen después.
        """
        revision = self._revision(tipo="reparacion")

        tardio = self._chequeo_catalogo(aplica_reparacion=True, name="Chequeo tardío")
        self.assertNotIn(tardio, revision.chequeo_ids.mapped("chequeo_id"))

        revision.action_actualizar_checklist()

        self.assertIn(tardio, revision.chequeo_ids.mapped("chequeo_id"))

    def test_actualizar_el_checklist_no_toca_lo_ya_respondido(self):
        """El botón solo agrega. Si pudiera pisar una respuesta, apretarlo sería un riesgo y
        nadie lo apretaría."""
        primero = self._chequeo_catalogo(aplica_reparacion=True, name="Chequeo temprano")
        revision = self._revision(tipo="reparacion")
        respondida = revision.chequeo_ids.filtered(lambda linea: linea.chequeo_id == primero)
        respondida.resultado = "no_ok"
        respondida.detalle = "El sello llegó roto."

        self._chequeo_catalogo(aplica_reparacion=True, name="Chequeo tardío")
        revision.action_actualizar_checklist()

        self.assertEqual(respondida.resultado, "no_ok")
        self.assertEqual(respondida.detalle, "El sello llegó roto.")

    def test_una_revision_confirmada_no_cambia_de_checklist(self):
        """Una ficha cerrada que crece deja de ser el registro de lo que se revisó ese día."""
        revision = self._revision()
        self._corrida_completa(revision)
        self._responder_todo(revision)
        self._responder_sellos(revision)
        revision.action_confirmar()

        self._chequeo_catalogo(aplica_reparacion=True, name="Chequeo tardío")

        with self.assertRaises(UserError):
            revision.action_actualizar_checklist()

    def test_las_secciones_reparten_el_checklist_sin_perder_ni_repetir(self):
        """Los campos por sección son vistas de las mismas líneas, y la pantalla se arma con
        ellos: una línea que no caiga en ninguno es un chequeo que el técnico no va a ver
        nunca y que sin embargo le va a impedir confirmar.

        Este test es el que hay que mirar al agregar una sección a `SECCIONES`: si se agrega
        el valor y se olvida el campo, las líneas de esa sección quedan invisibles. Pasó al
        agregar `energia` y `comunicacion` en 19.0.14.1.0, y lo agarró acá.
        """
        revision = self._revision(tipo="reparacion")

        campos = (
            revision.chequeo_inspeccion_fisica_ids,
            revision.chequeo_energia_ids,
            revision.chequeo_presion_ids,
            revision.chequeo_leak_ids,
            revision.chequeo_comunicacion_ids,
            revision.chequeo_navegacion_ids,
            revision.chequeo_video_ids,
            revision.chequeo_luces_ids,
            revision.chequeo_accesorios_ids,
            revision.chequeo_otro_ids,
        )

        por_seccion = self.env["mc.rov.revision.chequeo"].browse()
        for campo in campos:
            por_seccion |= campo

        self.assertEqual(por_seccion, revision.chequeo_ids)
        self.assertEqual(sum(len(campo) for campo in campos), len(revision.chequeo_ids))


@tagged("post_install", "-at_install")
class TestCondicionesHeredadas(RevisionCommon):
    """Una revisión nueva nace con las condiciones de la anterior del mismo equipo.

    En el taller la fuente es la que es. Un ROV que vuelve cinco veces obligaba a contestar
    cinco veces lo mismo, y la quinta se contesta de memoria — que es cuando aparecen los
    datos malos.
    """

    def test_hereda_las_condiciones_de_la_anterior(self):
        self._revision(tipo="reparacion", alimentacion="Generador", tension_salida=48)

        nueva = self._revision(tipo="reparacion")

        self.assertEqual(nueva.alimentacion, "Generador")
        self.assertEqual(nueva.tension_salida, 48)

    def test_no_hereda_resultados(self):
        """Heredar una medición sería inventar un dato."""
        self._revision(tipo="reparacion", alimentacion="Generador", subida=95.0)

        nueva = self._revision(tipo="reparacion")

        self.assertEqual(nueva.alimentacion, "Generador")
        self.assertFalse(nueva.subida)

    def test_lo_que_viene_en_vals_manda(self):
        self._revision(tipo="reparacion", alimentacion="Generador")

        nueva = self._revision(tipo="reparacion", alimentacion="UPS")

        self.assertEqual(nueva.alimentacion, "UPS")

    def test_terreno_no_hereda_del_taller(self):
        """La alimentación de un muelle no dice nada de la de un banco."""
        self._revision(tipo="rendimiento", alimentacion="Transformador")

        nueva = self._revision(tipo="terreno")

        self.assertFalse(nueva.alimentacion)


class TestFichaCongelada(RevisionCommon):
    """Una revisión confirmada es un documento: su contenido no puede cambiar después.

    Los campos «según la ficha» eran `related` en vivo hasta 19.0.18.2.0, así que una
    revisión de hace seis meses mostraba la ficha de hoy — y `luces_difieren` llegaba a dejar
    de marcar una diferencia que sí marcó el día de la prueba.
    """

    def test_la_foto_se_toma_al_crear(self):
        """Para que el técnico vea contra qué compara desde el primer minuto."""
        self.lot.mc_cantidad_luces = 6

        revision = self._revision(tipo="rendimiento")

        self.assertEqual(revision.luces_ficha, 6)

    def test_confirmar_refresca_la_foto_una_ultima_vez(self):
        """Si la ficha se corrigió mientras la prueba estaba a medio llenar, manda lo corregido."""
        self.lot.mc_cantidad_luces = 6
        revision = self._revision(tipo="rendimiento")
        self.lot.mc_cantidad_luces = 4

        revision._refrescar_ficha()

        self.assertEqual(revision.luces_ficha, 4)

    def test_confirmada_no_cambia_aunque_cambie_la_ficha(self):
        self.lot.mc_cantidad_luces = 6
        revision = self._revision(tipo="rendimiento")
        revision.estado = "confirmado"

        self.lot.mc_cantidad_luces = 4
        revision.invalidate_recordset()

        self.assertEqual(revision.luces_ficha, 6, "el documento conserva lo que declaró")

    def test_el_hallazgo_de_luces_tampoco_se_borra(self):
        """Lo peor del defecto: un documento entregado dejaba de marcar la diferencia."""
        self.lot.mc_cantidad_luces = 6
        revision = self._revision(tipo="rendimiento", luces_internas=2, luces_externas=2)
        revision.estado = "confirmado"
        self.assertTrue(revision.luces_difieren)

        self.lot.mc_cantidad_luces = 4
        revision.invalidate_recordset()

        self.assertTrue(revision.luces_difieren, "la diferencia que se entregó sigue marcada")


class TestPrecargaDesdeLaFicha(RevisionCommon):
    """La otra mitad del volcado: la prueba nace con lo que la ficha ya declara.

    Junto con el volcado hace que **el orden de trabajo deje de importar**: se llene primero
    la ficha o primero la prueba, nadie teclea lo mismo dos veces.
    """

    def test_la_prueba_de_rendimiento_nace_con_el_software_de_la_ficha(self):
        self.lot.mc_version_ardusub = "4.1.0"

        revision = self._revision(tipo="rendimiento")

        self.assertEqual(revision.version_ardusub_instalada, "4.1.0")

    def test_una_reparacion_no_se_precarga(self):
        """Ahí el software se compara: precargarlo borraría la diferencia que se busca."""
        self.lot.mc_version_ardusub = "4.1.0"

        revision = self._revision(tipo="reparacion")

        self.assertFalse(revision.version_ardusub_instalada)

    def test_lo_que_viene_en_vals_manda(self):
        self.lot.mc_version_ardusub = "4.1.0"

        revision = self._revision(tipo="rendimiento", version_ardusub_instalada="4.0.2")

        self.assertEqual(revision.version_ardusub_instalada, "4.0.2")


class TestBorradoDeRevisiones(RevisionCommon):
    """El botón crea al primer clic, así que hay que poder deshacerlo."""

    def test_un_borrador_se_puede_borrar(self):
        revision = self._revision(tipo="rendimiento")
        revision.unlink()
        self.assertFalse(revision.exists())

    def test_una_confirmada_no(self):
        """Es evidencia, y un entregable al cliente."""
        revision = self._revision(tipo="rendimiento")
        revision.estado = "confirmado"

        with self.assertRaises(UserError):
            revision.unlink()


class TestSoftwareALaFicha(RevisionCommon):
    """La prueba de rendimiento escribe en la ficha las versiones que se instalaron.

    En reparación el software se compara contra la ficha; acá es al revés, porque el equipo
    acaba de nacer y no hay contra qué comparar (§ 5.4).
    """

    def _rendimiento(self, version="4.1.0", **vals):
        revision = self._revision(tipo="rendimiento", version_ardusub_instalada=version, **vals)
        revision.estado = "confirmado"
        return revision

    def test_confirmar_llena_la_ficha_vacia(self):
        """Sin esto la ficha queda vacía y la comparación de reparación no funciona nunca."""
        self.assertFalse(self.lot.mc_version_ardusub)

        self._rendimiento()._volcar_a_la_ficha()

        self.assertEqual(self.lot.mc_version_ardusub, "4.1.0")

    def test_sobrescribe_un_valor_anterior(self):
        """Dejar la versión vieja haría que cada reparación registrara una diferencia falsa."""
        self.lot.mc_version_ardusub = "4.0.2"

        self._rendimiento(version="4.1.0")._volcar_a_la_ficha()

        self.assertEqual(self.lot.mc_version_ardusub, "4.1.0")

    def test_una_prueba_antigua_no_pisa_la_ficha_de_hoy(self):
        """Confirmar no ocurre en orden cronológico, y ésa es la trampa.

        Corregirle una errata a una prueba de hace dos años la vuelve a confirmar, y sin esta
        guarda escribiría en la ficha valores de hace dos años. Manda la más reciente, no la
        que se está confirmando — mismo criterio que `ultima_mantencion`.
        """
        antigua = self._rendimiento(version="4.0.2", fecha="2024-01-15")
        self._rendimiento(version="4.1.0", fecha="2026-08-20")._volcar_a_la_ficha()

        antigua._volcar_a_la_ficha()

        self.assertEqual(self.lot.mc_version_ardusub, "4.1.0")

    def test_una_reparacion_no_escribe_la_ficha(self):
        """Ahí el software se compara, no se determina."""
        self.lot.mc_version_ardusub = "4.0.2"
        revision = self._revision(tipo="reparacion", version_ardusub_instalada="9.9.9")
        revision.estado = "confirmado"

        revision._volcar_a_la_ficha()

        self.assertEqual(self.lot.mc_version_ardusub, "4.0.2")

    def test_lo_que_no_se_anoto_no_borra_la_ficha(self):
        """Un campo vacío en la prueba no es una afirmación sobre el equipo."""
        self.lot.mc_version_software = "ROVControl 2.3"

        self._rendimiento()._volcar_a_la_ficha()

        self.assertEqual(self.lot.mc_version_software, "ROVControl 2.3")

    def test_los_ajustes_se_vuelcan_desde_una_prueba_de_aceptacion(self):
        """Pilot gain y ganancia luz se miden en rendimiento y en terreno."""
        revision = self._revision(tipo="terreno", limitacion_pilot_gain=80)
        revision.estado = "confirmado"

        revision._volcar_a_la_ficha()

        self.assertEqual(self.lot.mc_limitacion_pilot_gain, 80)

    def test_una_reparacion_tambien_vuelca_los_ajustes(self):
        """El taller ajusta el pilot gain al reparar, no solo en las pruebas de aceptación.

        Lo confirmó Paulo el 2026-08-21 y corrige lo que decía el § 5.4. Por eso manda la
        revisión más reciente del equipo sea del tipo que sea.
        """
        self.lot.mc_limitacion_pilot_gain = 60
        revision = self._revision(tipo="reparacion", limitacion_pilot_gain=80)
        revision.estado = "confirmado"

        revision._volcar_a_la_ficha()

        self.assertEqual(self.lot.mc_limitacion_pilot_gain, 80)

    def test_el_conteo_de_luces_nunca_se_vuelca(self):
        """El contraejemplo de la regla, y por eso tiene test propio.

        La ficha dice cuántas luces DEBERÍA tener el equipo; la prueba cuenta cuántas
        encendieron. Si la prueba escribiera la ficha, una luz quemada se volvería la nueva
        especificación y `luces_difieren` no volvería a avisar nunca. Ahí la diferencia **es**
        el hallazgo.
        """
        self.lot.mc_cantidad_luces = 6
        revision = self._rendimiento(luces_internas=2, luces_externas=2)

        revision._volcar_a_la_ficha()

        self.assertEqual(self.lot.mc_cantidad_luces, 6)
        self.assertTrue(revision.luces_difieren)

    def test_el_cambio_queda_en_el_chatter_del_equipo(self):
        """Escribir en la ficha de otro registro sin dejar rastro es lo que el módulo evita."""
        mensajes_antes = len(self.lot.message_ids)

        self._rendimiento()._volcar_a_la_ficha()

        self.assertGreater(len(self.lot.message_ids), mensajes_antes)


class TestMcRovRevisionResultado(RevisionCommon):
    """Tests de `resultado`, que se deriva y no se decide."""

    def test_terreno_se_aprueba_sin_corrida_de_resistencia(self):
        """El funcionamiento continuo se exige solo donde es parte de la batería.

        Hasta `19.0.16.0.0` se exigía siempre, así que **una revisión de terreno no podía
        quedar aprobada nunca**: se quedaba en blanco para siempre. Y en terreno no hay
        corrida de resistencia — el criterio no es la relevancia sino la física, no hay dónde
        dejar un equipo andando hora y media colgado de un bote.
        """
        revision = self._revision(tipo="terreno")
        self._responder_todo(revision)

        self.assertFalse(
            revision.funcionamiento_continuo_resultado, "en terreno no se corre el esfuerzo"
        )
        self.assertEqual(revision.resultado, "aprobado")

    def test_rendimiento_sigue_exigiendo_la_corrida(self):
        """El arreglo no puede convertirse en dejar de pedirlo donde sí corresponde."""
        revision = self._revision(tipo="rendimiento")
        self._responder_todo(revision)

        self.assertFalse(
            revision.resultado, "sin funcionamiento continuo no hay resultado posible"
        )

    def test_sin_hallazgos_ni_fallas_el_revision_esta_aprobado(self):
        revision = self._revision()
        self._corrida_completa(revision)
        self._responder_todo(revision)

        self.assertEqual(revision.resultado, "aprobado")

    def test_un_hallazgo_cualquiera_lo_deja_con_observaciones(self):
        revision = self._revision()
        self._corrida_completa(revision)
        self._responder_todo(revision)
        self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
                "severidad": "informativo",
            }
        )

        self.assertEqual(revision.resultado, "aprobado_con_observaciones")

    def test_un_hallazgo_que_impide_operar_lo_rechaza(self):
        revision = self._revision()
        self._corrida_completa(revision)
        self._responder_todo(revision)
        self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_no_responde").id,
                "severidad": "impide_operar",
            }
        )

        self.assertEqual(revision.resultado, "rechazado")

    def test_un_chequeo_fallado_rechaza_aunque_nadie_escriba_el_hallazgo(self):
        """El equipo no pasó, y eso no se compensa con que nadie haya explicado por qué."""
        revision = self._revision()
        self._corrida_completa(revision)
        self._responder_todo(revision)
        revision.chequeo_ids[0].resultado = "no_ok"

        self.assertEqual(revision.resultado, "rechazado")

    def test_un_funcionamiento_continuo_con_problemas_rechaza(self):
        revision = self._revision()
        self._corrida_completa(revision, funcionamiento_continuo_resultado="con_problemas")
        self._responder_todo(revision)

        self.assertEqual(revision.resultado, "rechazado")

    def test_no_aplica_no_es_una_falla(self):
        """Un equipo sin joystick no está reprobado por no tenerlo."""
        revision = self._revision()
        self._corrida_completa(revision)
        self._responder_todo(revision, resultado="no_lo_tiene")

        self.assertEqual(revision.resultado, "aprobado")


@tagged("post_install", "-at_install")
class TestMcRovRevisionConfirmacion(RevisionCommon):
    """Tests de lo que se exige para confirmar."""

    def test_una_linea_de_chequeo_se_nombra_por_su_chequeo(self):
        """Es lo que se ve en el desplegable «Detectado por» al registrar un hallazgo.

        Sin `_compute_display_name` el modelo no tiene `name` ni `_rec_name` y Odoo cae en
        "mc.rov.revision.chequeo,50". Con un identificador técnico ahí no se puede elegir cuál
        prueba destapó el hallazgo, que es el eje de detección del análisis: un hallazgo
        frecuente que ningún chequeo detecta es un chequeo que falta.
        """
        revision = self._revision(tipo="reparacion")
        linea = revision.chequeo_ids[0]

        self.assertIn(linea.chequeo_id.name, linea.display_name)
        self.assertNotIn("mc.rov.revision.chequeo,", linea.display_name)

    def test_un_hallazgo_se_nombra_por_donde_y_que(self):
        """Es lo que se ve en «Resuelve el hallazgo», el campo que cierra el circuito.

        Mismo caso que la línea de chequeo. Si ahí sale un identificador técnico nadie enlaza
        el trabajo con el hallazgo, y la línea queda con «por qué pasó» y sin «qué se
        encontró» — que es justo el cruce que el análisis necesita.
        """
        revision = self._revision()
        hallazgo = self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
            }
        )

        self.assertIn("Motor", hallazgo.display_name)
        self.assertIn("Corrosión", hallazgo.display_name)
        self.assertNotIn("mc.rov.revision.hallazgo,", hallazgo.display_name)

    def test_la_bateria_cubre_energia_y_comunicacion(self):
        """Eran dos familias enteras del catálogo de síntomas sin ninguna prueba que las mirara.

        Un ROV que no enciende o que pierde conexión se iba a diagnosticar mirando, y el
        hallazgo quedaría sin «Prueba que lo detectó» — indistinguible de un chequeo que falta,
        que es justo lo que faltaba.
        """
        revision = self._revision(tipo="reparacion")

        secciones = set(revision.chequeo_ids.mapped("seccion"))

        self.assertIn("energia", secciones)
        self.assertIn("comunicacion", secciones)
        self.assertIn("inspeccion_fisica", secciones)

    def test_depth_hold_y_stabilize_son_dos_chequeos(self):
        """Apuntan a lugares distintos: el sensor de presión y el IMU o el compás.

        Y de tenerlos separados sale la deducción que no existe de otro modo: si depth hold
        falla pero stabilize funciona, el problema es el sensor de profundidad, porque uno
        depende del otro. Fusionarlos la haría imposible.
        """
        revision = self._revision(tipo="reparacion")
        chequeos = revision.chequeo_ids.mapped("chequeo_id")

        self.assertIn(self.env.ref("mc_rov.chequeo_depth_hold"), chequeos)
        self.assertIn(self.env.ref("mc_rov.chequeo_stabilize"), chequeos)

    def test_una_linea_de_chequeo_se_puede_buscar_escribiendo(self):
        """Mostrar bien el nombre no alcanza: hay que poder filtrar escribiendo.

        Odoo busca por `_rec_name` y este modelo no tiene ninguno, así que sin el override de
        `_search_display_name` escribir en el desplegable no matchea nada y la única salida es
        abrir «Buscar más» y recorrer veinte filas a ojo.
        """
        revision = self._revision(tipo="reparacion")
        linea = revision.chequeo_ids[0]
        palabra = linea.chequeo_id.name.split()[0]

        encontradas = self.env["mc.rov.revision.chequeo"].search(
            [("id", "in", revision.chequeo_ids.ids), ("display_name", "ilike", palabra)]
        )

        self.assertIn(linea, encontradas)

    def test_un_hallazgo_se_puede_buscar_por_componente(self):
        """El desplegable de «Resuelve el hallazgo» lista los del equipo, no los de una
        revisión, así que desde la segunda visita la lista es larga y buscar es la única
        forma razonable de elegir."""
        revision = self._revision()
        hallazgo = self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
                "componente_id": self.env.ref("mc_rov.comp_umbilical").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
            }
        )

        por_componente = self.env["mc.rov.revision.hallazgo"].search(
            [("display_name", "ilike", "Umbilical")]
        )
        por_hallazgo = self.env["mc.rov.revision.hallazgo"].search(
            [("display_name", "ilike", "Corrosión")]
        )

        self.assertIn(hallazgo, por_componente)
        self.assertIn(hallazgo, por_hallazgo)

    def test_una_revision_tiene_un_solo_umbilical(self):
        """Una revisión es una prueba completa bajo una condición, y el cable es la condición.

        Eran una lista hasta 19.0.15.0.0, para comparar dos cables dentro de la misma ficha.
        Pero las dos corridas compartían un solo juego de respuestas, así que cualquier
        chequeo que cambiara entre cables se perdía en silencio. Comparar dos cables son dos
        revisiones, cada una con su batería.
        """
        self.assertNotIn("corrida_ids", self.env["mc.rov.revision"]._fields)
        self.assertNotIn("mc.rov.revision.corrida", self.env)

        revision = self._corrida_completa(self._revision(), temperatura_interior=48.0)

        self.assertEqual(revision.umbilical, "equipo")
        self.assertEqual(revision.temperatura_interior, 48.0)

    def test_sin_funcionamiento_continuo_no_deja_confirmar(self):
        """La corrida siempre se hace, incluso al comparar un cable.

        Una revisión sin ese resultado dice que no se probó nada.
        """
        revision = self._revision()
        self._responder_todo(revision)

        with self.assertRaises(UserError):
            revision.action_confirmar()

    def test_con_chequeos_sin_responder_no_deja_confirmar(self):
        revision = self._revision()
        self._corrida_completa(revision)

        with self.assertRaises(UserError):
            revision.action_confirmar()

    def test_media_medicion_no_deja_confirmar(self):
        """Subida sin bajada parece un dato y no lo es."""
        revision = self._revision()
        self._corrida_completa(revision, subida=90.0)
        self._responder_todo(revision)

        with self.assertRaises(UserError):
            revision.action_confirmar()

    def test_un_funcionamiento_continuo_sin_duracion_no_deja_confirmar(self):
        """Cuánto aguantó es información distinta de si pasó."""
        revision = self._revision()
        self._corrida_completa(revision, funcionamiento_continuo_duracion=0.0)
        self._responder_todo(revision)

        with self.assertRaises(UserError):
            revision.action_confirmar()

    def test_un_revision_completo_se_confirma(self):
        revision = self._revision()
        self._corrida_completa(revision)
        self._responder_todo(revision)
        self._responder_sellos(revision)

        revision.action_confirmar()

        self.assertEqual(revision.estado, "confirmado")

    def test_el_mensaje_de_error_nombra_todo_lo_que_falta_de_una_vez(self):
        """Descubrir los faltantes de a uno, guardando entre medio, es la forma más segura
        de que el técnico abandone.

        Se comprueba sobre el mensaje que ve el usuario y no sobre el método interno: lo
        que importa es que enumere, no cómo lo calcula.
        """
        revision = self._revision()
        revision.responsable_id = False

        with self.assertRaises(UserError) as error:
            revision.action_confirmar()

        # El mensaje lista con viñetas; más de una significa que no se rindió en el primero.
        self.assertGreaterEqual(str(error.exception).count("·"), 2)

    def test_se_puede_volver_a_borrador(self):
        revision = self._revision()
        self._corrida_completa(revision)
        self._responder_todo(revision)
        self._responder_sellos(revision)
        revision.action_confirmar()

        revision.action_volver_a_borrador()

        self.assertEqual(revision.estado, "borrador")


@tagged("post_install", "-at_install")
class TestMcRovRevisionLuces(RevisionCommon):
    """Tests de la comparación contra la ficha técnica del equipo."""

    def test_el_conteo_de_luces_se_suma_solo(self):
        revision = self._revision(luces_internas=2, luces_externas=4)

        self.assertEqual(revision.luces_total, 6)

    def test_avisa_cuando_el_conteo_no_cuadra_con_la_ficha(self):
        """Si el ROV debería tener seis luces y se contaron cuatro, el sistema lo dice sin
        que nadie tenga que acordarse de comparar."""
        self.lot.mc_cantidad_luces = 6
        revision = self._revision(luces_internas=2, luces_externas=2)

        self.assertTrue(revision.luces_difieren)

    def test_no_avisa_cuando_la_ficha_no_dice_cuantas_hay(self):
        """Sin referencia no hay comparación posible: la alerta se calla en vez de mentir."""
        self.lot.mc_cantidad_luces = 0
        revision = self._revision(luces_internas=2, luces_externas=2)

        self.assertFalse(revision.luces_difieren)


@tagged("post_install", "-at_install")
class TestMcRovRevisionTrazabilidad(RevisionCommon):
    """Tests del circuito hallazgo → trabajo, que es lo que hace servible al modelo."""

    def test_una_linea_de_trabajo_apunta_al_hallazgo_que_resuelve(self):
        revision = self._revision()
        hallazgo = self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
            }
        )
        orden = self.env["repair.order"].create(
            {"product_id": self.product.id, "lot_id": self.lot.id}
        )

        linea = self.env["mc.rov.linea.falla"].create(
            {
                "repair_id": orden.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "accion_id": self.env.ref("mc_rov.accion_reparacion").id,
                "hallazgo_origen_id": hallazgo.id,
                "responsable_id": self.empleado.id,
                # Era `causa_raiz: "corrosion"` hasta 19.0.13.0.0. La corrosión no era una
                # causa raíz sino un mecanismo —de hecho es una entrada del catálogo de
                # hallazgos, la que usa este mismo test— y por eso el campo se partió: el
                # hallazgo dice QUÉ pasó y el origen, de quién es el problema.
                "origen": "desgaste",
            }
        )

        self.assertEqual(linea.hallazgo_origen_id, hallazgo)
        self.assertEqual(linea.responsable_id, self.empleado)
        self.assertEqual(linea.origen, "desgaste")

    def test_el_hallazgo_sabe_de_que_equipo_es(self):
        """lot_id almacenado en la línea es lo que permite agregar hallazgos por equipo sin
        pasar por la revisión en cada consulta."""
        revision = self._revision()
        hallazgo = self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
            }
        )

        self.assertEqual(hallazgo.lot_id, self.lot)

    def test_el_equipo_acumula_su_historial_de_revisiones(self):
        """Dos revisiones del mismo equipo son la serie de tiempo: es lo que deja ver que
        el ancho de banda cayó entre una visita y la siguiente."""
        self._revision(tipo="reparacion", fecha=fields.Date.to_date("2026-01-15"))
        self._revision(tipo="reparacion", fecha=fields.Date.to_date("2026-06-20"))

        self.assertEqual(len(self.lot.revision_ids), 2)
        self.assertEqual(self.lot.mc_revision_count, 2)


@tagged("post_install", "-at_install")
class TestMcRovRevisionSellos(RevisionCommon):
    """Tests de la inspección de sellos, que reemplazó a tres casillas independientes."""

    def test_la_reparacion_trae_una_fila_por_componente_sellado(self):
        revision = self._revision(tipo="reparacion")

        self.assertTrue(revision.inspeccion_ids)
        componentes = revision.inspeccion_ids.mapped("componente_id")
        self.assertTrue(all(componentes.mapped("es_inspeccionable")))

    def test_la_prueba_de_rendimiento_no_lleva_inspeccion_de_sellos(self):
        """En un equipo recién armado no hay sello previo que mirar."""
        self.assertFalse(self._revision(tipo="rendimiento").inspeccion_ids)

    def test_terreno_tampoco_lleva_inspeccion_de_sellos(self):
        """Una prueba en terreno no es una entrada al taller: el equipo no cambió de manos
        y nadie está evaluando cómo llegó."""
        self.assertFalse(self._revision(tipo="terreno").inspeccion_ids)

    def test_un_sello_roto_al_recibir_es_manipulacion_externa(self):
        """El taller nunca rompe un sello sin registrarlo, y sus roturas ocurren durante el
        trabajo — después de recibir. Así que roto al recibir no tiene ambigüedad."""
        revision = self._revision(tipo="reparacion")
        linea = revision.inspeccion_ids[0]

        linea.estado_sello = "roto"

        self.assertTrue(linea.manipulacion_externa)

    def test_un_sello_ausente_al_recibir_tambien_lo_es(self):
        """Que no esté es tan informativo como que esté roto: alguien lo sacó."""
        revision = self._revision(tipo="reparacion")
        linea = revision.inspeccion_ids[0]

        linea.estado_sello = "ausente"

        self.assertTrue(linea.manipulacion_externa)

    def test_un_equipo_sin_sello_previo_no_es_manipulacion(self):
        """Primera visita de un equipo que nunca vino: no hay nada que hayan roto."""
        revision = self._revision(tipo="reparacion")
        linea = revision.inspeccion_ids[0]

        linea.estado_sello = "sin_sello_previo"

        self.assertFalse(linea.manipulacion_externa)

    def test_un_sello_intacto_no_es_manipulacion(self):
        revision = self._revision(tipo="reparacion")
        linea = revision.inspeccion_ids[0]

        linea.estado_sello = "intacto"

        self.assertFalse(linea.manipulacion_externa)

    def test_no_deja_confirmar_con_sellos_sin_revisar(self):
        revision = self._revision(tipo="reparacion")
        self._corrida_completa(revision)
        self._responder_todo(revision)

        with self.assertRaises(UserError):
            revision.action_confirmar()

    def test_confirma_cuando_los_sellos_estan_revisados(self):
        revision = self._revision(tipo="reparacion")
        self._corrida_completa(revision)
        self._responder_todo(revision)
        revision.inspeccion_ids.write({"estado_sello": "intacto"})

        revision.action_confirmar()

        self.assertEqual(revision.estado, "confirmado")


@tagged("post_install", "-at_install")
class TestMcRovRevisionAutomatica(RevisionCommon):
    """Tests de la revisión que se abre sola al entrar el equipo al taller."""

    def _orden(self, **vals):
        return self.env["repair.order"].create(
            {"product_id": self.product.id, "lot_id": self.lot.id, **vals}
        )

    def _revisiones(self, orden):
        return self.env["mc.rov.revision"].search([("repair_id", "=", orden.id)])

    def _lista_para_confirmar(self, revision, **vals):
        """Una revisión a la que solo le falta lo que el test quiera probar."""
        revision.responsable_id = self.empleado
        revision.write(
            {
                "umbilical": "equipo",
                "largo": 100.0,
                "alimentacion": "Generador",
                "funcionamiento_continuo_duracion": 1.5,
                "funcionamiento_continuo_resultado": "ok",
                **vals,
            }
        )
        revision.chequeo_ids.write({"resultado": "ok"})
        revision.inspeccion_ids.write({"estado_sello": "intacto"})
        return revision

    def test_una_revision_a_medio_llenar_no_dice_aprobado(self):
        """Hasta 19.0.15.1.0 caía en «Aprobado» por descarte.

        Una ficha recién creada —22 chequeos sin responder, nada probado— declaraba que el
        equipo estaba bien. Es el vacío indistinguible de un dato, y del lado optimista, que
        es el peor de los dos.
        """
        orden = self._orden()
        orden.state = "confirmed"
        revision = self._revisiones(orden)

        self.assertFalse(revision.resultado)

        self._lista_para_confirmar(revision)

        self.assertEqual(revision.resultado, "aprobado")

    def test_la_primera_revision_trae_su_motivo_por_defecto(self):
        """No cuesta un clic y evita que «vacío» signifique «es la primera»."""
        orden = self._orden()
        orden.state = "confirmed"

        self.assertEqual(self._revisiones(orden).motivo, "primer_diagnostico")

    def test_la_segunda_revision_no_se_confirma_sin_motivo(self):
        """Dos revisiones en una visita pueden ser dos cosas muy distintas.

        Un re-test tras reparación y una comparación de cable se ven idénticos, y contarlos
        juntos arruina la pregunta que justifica el segundo pase: «¿cuántas veces todavía
        muestra la falla?». Sin el motivo, la mitad de esos segundos pases podrían ser
        comparaciones de cable y el número no significaría nada.
        """
        orden = self._orden()
        orden.state = "confirmed"
        orden.action_nueva_revision()
        segunda = self._revisiones(orden).filtered(lambda r: r.numero_en_visita == 2)
        self._lista_para_confirmar(segunda)

        self.assertFalse(segunda.motivo)
        with self.assertRaises(UserError):
            segunda.action_confirmar()

        segunda.motivo = "comparacion_cable"
        segunda.action_confirmar()

        self.assertEqual(segunda.estado, "confirmado")

    def test_la_primera_revision_se_confirma_sin_que_nadie_elija_motivo(self):
        """El motivo se exige siempre que haya visita, y aun así la primera no cuesta un clic.

        Lo resuelve el valor por defecto: la revisión que se abre sola al confirmar la orden
        nace con «primer diagnóstico», que es lo que es. La que hay que contestar a mano es la
        segunda, que es la única ambigua.
        """
        orden = self._orden()
        orden.state = "confirmed"
        primera = self._revisiones(orden)

        self._lista_para_confirmar(primera)
        primera.action_confirmar()

        self.assertEqual(primera.numero_en_visita, 1)
        self.assertEqual(primera.motivo, "primer_diagnostico")
        self.assertEqual(primera.estado, "confirmado")

    def test_una_orden_en_borrador_no_abre_revision(self):
        """Un borrador es una cotización: el equipo puede no haber llegado."""
        self.assertFalse(self._revisiones(self._orden()))

    def test_confirmar_la_orden_abre_la_revision(self):
        """Siempre ocurre, así que no puede depender de que alguien apriete un botón."""
        orden = self._orden()

        orden.state = "confirmed"

        revisiones = self._revisiones(orden)
        self.assertEqual(len(revisiones), 1)
        self.assertEqual(revisiones.tipo, "reparacion")

    def test_no_se_duplica_al_avanzar_de_estado(self):
        orden = self._orden()

        orden.state = "confirmed"
        orden.state = "under_repair"

        self.assertEqual(len(self._revisiones(orden)), 1)

    def test_cancelar_no_abre_revision(self):
        orden = self._orden()

        orden.state = "cancel"

        self.assertFalse(self._revisiones(orden))

    def test_una_orden_sin_rov_no_abre_revision(self):
        """Una reparación de componente no lleva revisión técnica."""
        product_ajeno = self.env["product.product"].create(
            {"name": "Componente Test Rev", "tracking": "serial"}
        )
        lot_ajeno = self.env["stock.lot"].create(
            {"name": "COMP-REV-001", "product_id": product_ajeno.id}
        )
        orden = self.env["repair.order"].create(
            {"product_id": product_ajeno.id, "lot_id": lot_ajeno.id}
        )

        orden.state = "confirmed"

        self.assertFalse(self._revisiones(orden))

    def test_el_boton_abre_una_segunda_revision_de_la_misma_visita(self):
        """El segundo pase —se prueba, se arregla, se vuelve a probar— sí se pide a mano.
        `numero_en_visita` es lo que después distingue con qué llegó de cómo quedó."""
        orden = self._orden()
        orden.state = "confirmed"

        orden.action_nueva_revision()

        revisiones = self._revisiones(orden)
        self.assertEqual(len(revisiones), 2)
        self.assertEqual(sorted(revisiones.mapped("numero_en_visita")), [1, 2])
