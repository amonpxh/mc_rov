"""Contratos de volumen y Pareto sin base de datos ni reloj global."""

import copy
import unittest

try:
    import production_kpi_metrics as metrics
except ModuleNotFoundError:
    metrics = None


class TestProductionMetrics(unittest.TestCase):
    """Una repetición administrativa no produce otra unidad o visita."""

    def setUp(self):
        self.assertIsNotNone(metrics, "Falta agregación de volumen y Pareto")

    def event(self, kind="repair_done", identity="repair:1", **values):
        return {
            "kind": kind,
            "identity": identity,
            "at": "2026-11-12 12:00:00",
            "lot_id": 1,
            "revision_key": "bom:1:v2",
            **values,
        }

    def observation(self, key="obs:1", **values):
        return {
            "identity": key,
            "finding_id": 1,
            "finding_label": "Corrosión",
            "component_id": 2,
            "component_label": "Motor",
            "visit_id": 3,
            "lot_id": 4,
            **values,
        }

    def test_empty_population_has_no_invented_counts(self):
        report = metrics.summarize_events([])
        self.assertEqual(report["repair"]["visits"], 0)
        self.assertEqual(report["manufacturing"]["manufactured"], 0)
        self.assertEqual(report["unknown_date"], 0)

    def test_three_visits_on_two_units(self):
        rows = [
            self.event(identity=f"repair:{key}", lot_id=1 if key < 3 else 2) for key in (1, 2, 3)
        ]
        report = metrics.summarize_events(rows)["repair"]
        self.assertEqual((report["visits"], report["equipment"]), (3, 2))

    def test_reclosing_does_not_add_visit_or_move_date(self):
        rows = [self.event(), self.event(at="2026-12-12 12:00:00")]
        report = metrics.summarize_events(rows, date_from="2026-12-01", date_to="2026-12-31")
        self.assertEqual(report["repair"]["visits"], 0)

    def test_period_uses_santiago_day_and_inclusive_end(self):
        rows = [
            self.event(at="2026-11-13 02:59:59"),
            self.event(identity="repair:2", at="2026-11-13 03:00:00"),
        ]
        report = metrics.summarize_events(rows, date_from="2026-11-12", date_to="2026-11-12")
        self.assertEqual(report["repair"]["visits"], 1)

    def test_unknown_date_is_separate(self):
        report = metrics.summarize_events([self.event(at=False)], date_from="2026-11-01")
        self.assertEqual(report["repair"]["visits"], 0)
        self.assertEqual(report["unknown_date"], 1)

    def test_partial_two_units_keep_separate_milestones(self):
        rows = [
            self.event("manufactured", "unit:1"),
            self.event("manufactured", "unit:2", lot_id=2),
            self.event("accepted", "unit:1"),
            self.event("released", "unit:1"),
        ]
        report = metrics.summarize_events(rows)["manufacturing"]
        self.assertEqual(
            [report[name] for name in ("manufactured", "accepted", "released", "outbound")],
            [2, 1, 1, 0],
        )

    def test_revision_filter_retains_unknown_separately(self):
        rows = [
            self.event(),
            self.event(identity="repair:2", revision_key="bom:1:v1"),
            self.event(identity="repair:3", revision_key=False),
        ]
        report = metrics.summarize_events(rows, revision=["bom:1:v2"])["repair"]
        self.assertEqual(report["visits"], 1)
        self.assertEqual(report["unknown_revision"], 1)

    def test_invalid_period_is_rejected(self):
        with self.assertRaises(ValueError):
            metrics.summarize_events([], date_from="2026-12-01", date_to="2026-11-01")

    def test_pareto_counts_observations_not_incidents(self):
        rows = [self.observation(str(key)) for key in (1, 2, 3)]
        report = metrics.pareto(rows)
        self.assertEqual(report["total"], 3)
        self.assertEqual(report["rows"][0]["count"], 3)
        self.assertEqual(report["unit"], "observations")

    def test_pareto_visit_deduplicates_within_category(self):
        rows = [self.observation(str(key)) for key in (1, 2, 3)]
        self.assertEqual(metrics.pareto(rows, unit="visits")["total"], 1)

    def test_pareto_keeps_other_and_unknown_in_denominator(self):
        rows = [
            self.observation("1"),
            self.observation("2"),
            self.observation("3", finding_id=2, finding_label="Fuga"),
            self.observation("4", finding_id=False, finding_label=False),
        ]
        report = metrics.pareto(rows, limit=1)
        self.assertEqual(report["total"], 4)
        self.assertEqual(report["unclassified"], 1)
        self.assertEqual(report["rows"][0]["percent"], 50)
        self.assertEqual(report["rows"][-1]["label"], "Otros")
        self.assertEqual(report["rows"][-1]["cumulative_percent"], 100)

    def test_pareto_reconfirmation_does_not_duplicate_observation(self):
        report = metrics.pareto([self.observation(), self.observation()])
        self.assertEqual(report["total"], 1)

    def test_inputs_are_not_mutated(self):
        events, observations = [self.event()], [self.observation()]
        before = copy.deepcopy((events, observations))
        metrics.summarize_events(events)
        metrics.pareto(observations)
        self.assertEqual((events, observations), before)

    def test_incident_unit_cannot_be_invented(self):
        with self.assertRaises(ValueError):
            metrics.pareto([], unit="incidents")


class TestProductionBalances(unittest.TestCase):
    """Los saldos reproducen hechos y reversos hasta la fecha de corte."""

    event = TestProductionMetrics.event

    def test_balances_use_all_history_at_cutoff(self):
        self.assertTrue(hasattr(metrics, "milestone_balances"), "Faltan saldos al corte")
        rows = [
            self.event("manufactured", "unit:1", at="2026-10-01 12:00:00"),
            self.event("accepted", "unit:1", at="2026-11-01 12:00:00"),
        ]
        report = metrics.milestone_balances(rows, date_to="2026-11-12")
        self.assertEqual(report["accepted_not_released"], 1)
        self.assertEqual(report["manufactured_not_accepted"], 0)

    def test_return_changes_balance_but_preserves_delivery_hito(self):
        self.assertTrue(hasattr(metrics, "milestone_balances"), "Faltan saldos al corte")
        rows = [
            self.event(kind, "unit:1")
            for kind in ("manufactured", "accepted", "released", "outbound")
        ]
        rows.append(
            self.event(
                "reversed",
                "move:1",
                at="2026-11-13 12:00:00",
                unit_identity="unit:1",
                reversal_of="outbound",
            )
        )
        self.assertEqual(metrics.milestone_balances(rows)["released_in_workshop"], 1)
        self.assertEqual(metrics.summarize_events(rows)["manufacturing"]["outbound"], 1)

    def test_return_then_redelivery_keeps_one_manufactured_unit(self):
        self.assertTrue(hasattr(metrics, "milestone_balances"), "Faltan saldos al corte")
        rows = [
            self.event(kind, "unit:1")
            for kind in ("manufactured", "accepted", "released", "outbound")
        ]
        rows += [
            self.event(
                "reversed",
                "move:1",
                at="2026-11-13 12:00:00",
                unit_identity="unit:1",
                reversal_of="outbound",
            ),
            self.event(
                "unit_movement",
                "move:2",
                at="2026-11-14 12:00:00",
                unit_identity="unit:1",
                effect="outbound",
            ),
        ]
        report = metrics.milestone_balances(rows)
        self.assertEqual(report["outbound"], 1)
        self.assertEqual(report["released_in_workshop"], 0)

    def test_unbuild_preserves_historical_manufacture(self):
        self.assertTrue(hasattr(metrics, "milestone_balances"), "Faltan saldos al corte")
        rows = [
            self.event("manufactured", "unit:1"),
            self.event(
                "reversed",
                "unbuild:1",
                at="2026-11-13 12:00:00",
                unit_identity="unit:1",
                reversal_of="manufactured",
            ),
        ]
        self.assertEqual(metrics.milestone_balances(rows)["unbuilt"], 1)
        self.assertEqual(metrics.summarize_events(rows)["manufacturing"]["manufactured"], 1)

    def test_protocol_reopen_changes_readiness_not_historical_hitos(self):
        rows = [self.event(kind, "unit:1") for kind in ("manufactured", "accepted", "released")]
        rows.append(
            self.event(
                "unit_movement",
                "reopen:1",
                at="2026-11-13 12:00:00",
                unit_identity="unit:1",
                effect="invalidate_acceptance",
            )
        )
        self.assertEqual(metrics.milestone_balances(rows)["manufactured_not_accepted"], 1)
        self.assertEqual(metrics.summarize_events(rows)["manufacturing"]["released"], 1)


class TestObservationCorrections(unittest.TestCase):
    """Corregir una observación conserva el original y no crea otra ocurrencia."""

    def test_amendment_replaces_category_without_extra_observation(self):
        self.assertTrue(
            hasattr(metrics, "project_observations"), "Falta proyección de correcciones"
        )
        original = {
            "kind": "observation",
            "identity": "finding:1",
            "at": "2026-11-10 12:00:00",
            "finding_id": 1,
        }
        amendment = {
            "kind": "observation_correction",
            "identity": "correction:1",
            "at": "2026-11-11 12:00:00",
            "observation_identity": "finding:1",
            "replacement": {"finding_id": 2},
            "detected_at": original["at"],
        }
        rows = metrics.project_observations([original, amendment])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["identity"], "finding:1")
        self.assertEqual(rows[0]["finding_id"], 2)
        self.assertEqual(original["finding_id"], 1)

    def test_audited_void_removes_occurrence_without_deleting_event(self):
        self.assertTrue(
            hasattr(metrics, "project_observations"), "Falta proyección de correcciones"
        )
        original = {"kind": "observation", "identity": "finding:1", "at": "2026-11-10 12:00:00"}
        amendment = {
            "kind": "observation_correction",
            "identity": "correction:1",
            "observation_identity": "finding:1",
            "replacement": False,
        }
        self.assertEqual(metrics.project_observations([original, amendment]), [])
        self.assertEqual(original["kind"], "observation")

    def test_latest_correction_keeps_corrected_detection_date(self):
        self.assertTrue(
            hasattr(metrics, "project_observations"), "Falta proyección de correcciones"
        )
        original = {"kind": "observation", "identity": "finding:1", "at": False}
        amendment = {
            "kind": "observation_correction",
            "identity": "correction:1",
            "observation_identity": "finding:1",
            "replacement": {},
            "detected_at": "2026-11-10 12:00:00",
        }
        self.assertEqual(
            metrics.project_observations([original, amendment])[0]["at"], amendment["detected_at"]
        )
