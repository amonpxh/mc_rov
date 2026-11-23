"""Agregados Q3 sobre líneas nativas de visitas con cierre acreditado."""

from collections import defaultdict
from math import isfinite


def summarize_rework(visits):
    """Usa una sola fila por línea y separa los denominadores con cobertura."""
    result = dict.fromkeys(
        (
            "closed_visits",
            "visits_with_rework",
            "complete_visits",
            "complete_visits_with_rework",
            "visits_without_lines",
            "pending_visits",
            "rework_lines",
            "planned_lines",
            "additional_lines",
            "pending_lines",
            "classified_hours",
            "pending_hours",
            "rework_hours",
            "missing_hours_lines",
        ),
        0,
    )
    causes = defaultdict(lambda: {"lines": 0, "hours": 0})
    result["closed_visits"] = len(visits)
    for rows in visits.values():
        states = {state for state, _hours, _origin in rows}
        has_rework = "rework" in states
        result["visits_with_rework"] += has_rework
        result["visits_without_lines"] += not rows
        result["pending_visits"] += "pending" in states
        if rows and "pending" not in states:
            result["complete_visits"] += 1
            result["complete_visits_with_rework"] += has_rework
        for state, hours, origin in rows:
            result[f"{state}_lines"] += 1
            known = isfinite(hours) and hours > 0
            result["missing_hours_lines"] += not known
            amount = hours if known else 0
            result["pending_hours" if state == "pending" else "classified_hours"] += amount
            if state == "rework":
                result["rework_hours"] += amount
                cause = causes[origin or "unknown"]
                cause["lines"] += 1
                cause["hours"] += amount
    for key in ("classified_hours", "pending_hours", "rework_hours"):
        result[key] = round(result[key], 2)
    for cause in causes.values():
        cause["hours"] = round(cause["hours"], 2)
    result["causes"] = dict(causes)
    result["visit_percent"] = _percent(
        result["complete_visits_with_rework"], result["complete_visits"]
    )
    result["hours_percent"] = _percent(result["rework_hours"], result["classified_hours"])
    return result


def _percent(numerator, denominator):
    return round(100 * numerator / denominator, 1) if denominator else None
