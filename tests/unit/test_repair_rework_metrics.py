"""Q3 distingue alcance, retrabajo confirmado y cobertura de horas."""

from unittest import TestCase

from repair_rework_metrics import summarize_rework


class TestRepairReworkMetrics(TestCase):
    """La evidencia compartida no multiplica horas ni visitas."""

    def test_multiple_corrections_count_one_visit(self):
        rows = {
            1: [("rework", 2, "diseno"), ("rework", 1, "desconocida"), ("additional", 3, False)],
            2: [("pending", 4, False), ("planned", 2, False), ("rework", 0, False)],
            3: [],
        }
        result = summarize_rework(rows)
        self.assertEqual(result["visits_with_rework"], 2)
        self.assertEqual(result["complete_visits"], 1)
        self.assertEqual(result["complete_visits_with_rework"], 1)
        self.assertEqual(result["visits_without_lines"], 1)
        self.assertEqual(result["pending_visits"], 1)
        self.assertEqual(result["visit_percent"], 100)
        self.assertEqual(result["rework_lines"], 3)
        self.assertEqual(result["rework_hours"], 3)
        self.assertEqual(result["classified_hours"], 8)
        self.assertEqual(result["pending_hours"], 4)
        self.assertEqual(result["missing_hours_lines"], 1)
        self.assertEqual(result["hours_percent"], 37.5)
        self.assertEqual(result["causes"]["desconocida"], {"lines": 1, "hours": 1})
        self.assertEqual(result["causes"]["unknown"], {"lines": 1, "hours": 0})

    def test_pending_proposal_has_no_rate(self):
        result = summarize_rework({1: [("pending", 5, "falla_fabricacion")]})
        self.assertEqual(result["pending_lines"], 1)
        self.assertEqual(result["visits_with_rework"], 0)
        self.assertIsNone(result["visit_percent"])
        self.assertIsNone(result["hours_percent"])
