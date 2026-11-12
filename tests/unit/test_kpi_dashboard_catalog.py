"""Las fichas permiten interpretar sus cifras y sus capturas pendientes."""

import unittest
import kpi_dashboard_catalog as catalog


class TestKPIDashboardCatalog(unittest.TestCase):
    """No basta el nombre del indicador para explicar su población o denominador."""

    def test_eleven_families_have_complete_definitions(self):
        self.assertTrue(hasattr(catalog, "DEFINITIONS"), "Faltan las definiciones completas")
        keys = {row[0] for row in catalog.INITIAL_FAMILIES}
        self.assertEqual(set(catalog.DEFINITIONS), keys)
        for row in catalog.DEFINITIONS.values():
            for field in ("decision", "source", "population", "formula"):
                self.assertIsInstance(row.get(field), str)
                self.assertGreater(len(row[field].strip()), 15)

    def test_first_pass_definition_distinguishes_rate_and_coverage(self):
        self.assertTrue(hasattr(catalog, "DEFINITIONS"), "Faltan las definiciones completas")
        row = catalog.DEFINITIONS["Q1"]
        self.assertIn("evaluados", row["formula"])
        self.assertIn("cobertura", row["formula"])
        self.assertIn("actual", row["population"])
