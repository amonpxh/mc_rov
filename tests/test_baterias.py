"""Qué chequeos pide cada tipo de prueba.

Vive en su propio archivo y no junto a los tests de la revisión porque lo que cubre es el
**catálogo**, que desde `19.0.20.0.0` es del usuario: se ajusta desde Configuración y va a
crecer sin pasar por un PR. Lo que se protege acá es el reparto que el módulo entrega.
"""

from pathlib import Path

from lxml import etree
from odoo.tests import tagged

from .test_mc_rov_revision import RevisionCommon


@tagged("post_install", "-at_install")
class TestBaterias(RevisionCommon):
    """Cuántos chequeos pide cada tipo, y por qué no son los mismos.

    El reparto es el del § 5.3 del diseño de fabricación y sale de dos criterios: un equipo
    recién armado **no tiene desgaste**, así que los chequeos que buscan daño de uso son de
    reparación; y en terreno vale solo **lo que se puede medir estando ahí**.

    Se cuenta y no se lista uno por uno a propósito: el catálogo es del usuario desde
    `19.0.20.0.0` y va a crecer. Lo que este test protege es el reparto estándar que el
    módulo entrega, no que el catálogo se quede quieto.
    """

    def _cuantos_estandar(self, tipo):
        """Cuenta la configuración entregada sin depender de ajustes del taller en la BD."""
        catalogo = etree.parse(
            str(Path(__file__).resolve().parents[1] / "data/mc_rov_revision_data.xml")
        )
        return len(
            catalogo.xpath(
                "//record[@model='mc.rov.chequeo']"
                f"[field[@name='aplica_{tipo}' and @eval='True']]"
            )
        )

    def test_reparacion_conserva_sus_24_chequeos(self):
        """El nuevo control de salida no amplía la batería estándar de reparación."""
        self.assertEqual(self._cuantos_estandar("reparacion"), 24)

    def test_rendimiento_no_pide_los_de_desgaste(self):
        self.assertEqual(self._cuantos_estandar("rendimiento"), 19)

    def test_terreno_conserva_estanqueidad_pero_no_salida_de_brazo(self):
        """Ambas prueban estanqueidad; la salida del brazo se comprueba en banco.

        En el muelle no hay máquina de presión, pero **el equipo baja igual**: la profundidad
        alcanzada no es un dato de contexto, es la misma verificación hecha por otro medio.
        Para estanqueidad cambia la medición —bar y tiempo en el taller, metros en
        terreno—, mientras que configurar la salida del brazo se comprueba solo en rendimiento.

        `19.0.20.0.0` la dejó fuera de terreno siguiendo la tabla de totales del § 5.3 del
        diseño, que se contradecía con su propio § 5.2. Manda el § 5.2, y lo levantó Paulo
        preguntando por qué faltaba.
        """
        self.assertEqual(self._cuantos_estandar("terreno"), 18)
        self.assertEqual(
            self._cuantos_estandar("rendimiento"), self._cuantos_estandar("terreno") + 1
        )

        estanqueidad = self.env.ref("mc_rov.chequeo_estanqueidad")
        self.assertTrue(estanqueidad.aplica_terreno)
        self.assertTrue(estanqueidad.aplica_rendimiento)
        self.assertTrue(estanqueidad.aplica_reparacion)

    def test_salida_de_brazo_se_genera_solo_en_rendimiento(self):
        brazo = self.env.ref("mc_rov.chequeo_salida_brazo")
        self.assertEqual(
            brazo.name,
            "Salida de brazo configurada, reconocida en software y operativa "
            "con brazos de corte y pinza",
        )
        self.assertEqual(brazo.nombre_ficha, "Salida de brazo")
        self.assertEqual(brazo.seccion, "accesorios")
        self.assertTrue(brazo.aplica_rendimiento)
        self.assertFalse(brazo.aplica_reparacion)
        self.assertFalse(brazo.aplica_terreno)

        for tipo in ("rendimiento", "terreno", "reparacion"):
            revision = self._revision(tipo=tipo)
            lineas = revision.chequeo_ids.filtered(lambda linea: linea.chequeo_id == brazo)
            self.assertEqual(len(lineas), 1 if tipo == "rendimiento" else 0)

    def test_los_de_desgaste_son_solo_de_reparacion(self):
        """Los cinco que el § 5.3 mueve, nombrados: el total no dice cuáles son."""
        for xmlid in (
            "chequeo_chasis",
            "chequeo_penetradores",
            "chequeo_helices_dano",
            "chequeo_umbilical_estado",
            "chequeo_helices",
        ):
            chequeo = self.env.ref(f"mc_rov.{xmlid}")
            self.assertTrue(chequeo.aplica_reparacion, xmlid)
            self.assertFalse(chequeo.aplica_rendimiento, xmlid)
            self.assertFalse(chequeo.aplica_terreno, xmlid)

    def test_el_software_de_superficie_se_pide_en_las_tres(self):
        """Se había acotado de más a reparación en 19.0.15.2.0."""
        chequeo = self.env.ref("mc_rov.chequeo_software_opera")
        self.assertTrue(chequeo.aplica_rendimiento)
        self.assertTrue(chequeo.aplica_terreno)
        self.assertTrue(chequeo.aplica_reparacion)
