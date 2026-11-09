"""Pure stage/event arithmetic; authorization and date normalization happen upstream."""

from datetime import date, datetime
from statistics import median


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _record_compliance(metric, finished, deadline):
    if not _is_date(finished) or not _is_date(deadline):
        metric["unknown"] += 1
        return
    metric["known"] += 1
    metric["on_time"] += int(finished <= deadline)


def _elapsed_hours(started, finished):
    # The adapter supplies UTC-naive instants. Mixed/unnormalized values are not evidence.
    if not isinstance(started, datetime) or not isinstance(finished, datetime):
        return None
    if started.tzinfo is not None or finished.tzinfo is not None or finished < started:
        return None
    return (finished - started).total_seconds() / 3600


def _record_pending(result, row):
    result["pending"] += 1
    result["pending_activity_missing"] += int(not row.get("activity_active"))
    deadline, cutoff = row.get("pending_deadline"), row.get("as_of_date")
    if _is_date(deadline) and _is_date(cutoff):
        result["overdue"] += int(deadline < cutoff)
    else:
        result["pending_timing_unknown"] += 1


def build_metrics(rows):
    """Return explicit coverage rather than presenting absent evidence as success."""
    result = {
        "pending": 0,
        "overdue": 0,
        "pending_timing_unknown": 0,
        "pending_activity_missing": 0,
        "completed": 0,
        "cancelled": 0,
        "manual_history": 0,
        "original_compliance": {"value": None, "on_time": 0, "known": 0, "unknown": 0},
        "current_compliance": {"value": None, "on_time": 0, "known": 0, "unknown": 0},
        "duration_hours": {"value": None, "known": 0, "unknown": 0},
    }
    durations = []
    for row in rows:
        outcome = row.get("outcome")
        if outcome not in ("pending", "business_done", "cancelled", "manual_done", "withdrawn"):
            raise ValueError("Unknown work KPI outcome")
        if outcome == "pending":
            _record_pending(result, row)
            continue
        if not row.get("in_period"):
            continue
        if outcome == "cancelled":
            result["cancelled"] += 1
            continue
        if outcome in ("manual_done", "withdrawn"):
            result["manual_history"] += 1
            continue
        result["completed"] += 1
        for prefix in ("original", "current"):
            _record_compliance(
                result[prefix + "_compliance"],
                row.get("finished_date"),
                row.get(prefix + "_deadline"),
            )
        hours = _elapsed_hours(row.get("started_at"), row.get("finished_at"))
        if hours is None:
            result["duration_hours"]["unknown"] += 1
        else:
            durations.append(hours)
    for prefix in ("original", "current"):
        metric = result[prefix + "_compliance"]
        if metric["known"]:
            metric["value"] = 100 * metric["on_time"] / metric["known"]
    if durations:
        result["duration_hours"].update(value=float(median(durations)), known=len(durations))
    return result
