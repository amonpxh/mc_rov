"""Qué chequeos pide cada tipo de prueba.

Vive en su propio archivo y no junto a los tests de la revisión porque lo que cubre es el
**catálogo**, que desde `19.0.20.0.0` es del usuario: se ajusta desde Configuración y va a
crecer sin pasar por un PR. Lo que se protege acá es el reparto que el módulo entrega.
"""

from odoo.tests import tagged

from .test_mc_rov_revision import RevisionCommon


@tagged("post_install", "-at_install")
class TestBaterias(RevisionCommon):
    """Cuántos chequeos pide cada tipo, y por qué no son los mismos.

    El reparto es el del § 5.3 del diseño de fabricación y sale de dos criterios: un equipo
    recién armado **no tiene desgaste**, así que los chequeos que buscan daño de uso son de
    reparación; y en terreno vale solo **lo que se puede medir estando ahí**.

    Se cuenta y no se lista uno por uno a propósito: el catálogo es del usuario desde
    `19.0.20.0.0` y va a crecer. Lo que este test protege es el reparto de los 24 que el
    módulo entrega, no que el catálogo se quede quieto.
    """

    def _cuantos(self, tipo):
        return self.env["mc.rov.chequeo"].search_count([(f"aplica_{tipo}", "=", True)])

    def test_una_reparacion_los_pide_todos(self):
        """El equipo llegó roto y no se sabe por qué: ahí se mira todo."""
        self.assertEqual(self._cuantos("reparacion"), 24)

    def test_rendimiento_no_pide_los_de_desgaste(self):
        self.assertEqual(self._cuantos("rendimiento"), 18)

    def test_terreno_es_rendimiento_menos_la_estanqueidad(self):
        """En el muelle no hay máquina de presión.

        La misma pregunta —¿se mantiene estanco?— la contesta ahí la profundidad alcanzada,
        que es la verificación de presión hecha por otro medio, no un dato de contexto.
        """
        self.assertEqual(self._cuantos("terreno"), 17)

        estanqueidad = self.env.ref("mc_rov.chequeo_estanqueidad")
        self.assertFalse(estanqueidad.aplica_terreno)
        self.assertTrue(estanqueidad.aplica_rendimiento)

    def test_los_de_desgaste_son_solo_de_reparacion(self):
        """Los cinco que el § 5.3 mueve, nombrados: contar 18 no dice cuáles son."""
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
