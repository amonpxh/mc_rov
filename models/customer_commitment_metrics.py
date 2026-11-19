"""F3 concilia promesas y salidas acreditadas sin consultar el ORM."""

from datetime import date, timezone
from itertools import groupby
from zoneinfo import ZoneInfo

_SANTIAGO = ZoneInfo("America/Santiago")
_STATUSES = ("on_time", "late", "overdue", "unknown", "cancelled")


def _santiago_day(at):
    return at.replace(tzinfo=timezone.utc).astimezone(_SANTIAGO).date()


def _day_and_time(value, day_field, time_field):
    at = value.get(time_field)
    return (_santiago_day(at) if at else value.get(day_field), at)


def _agreement_visible(agreement, as_of):
    recorded_at = agreement.get("recorded_at") or agreement["agreed_at"]
    return max(recorded_at, agreement["agreed_at"]) <= as_of


def _deadline_result(promise, completion, as_of):
    day, at = promise
    if day is None:
        return "undefined"
    if completion is None:
        expired = as_of > at if at else _santiago_day(as_of) > day
        return "overdue" if expired else "pending"
    exit_day, exit_at = completion
    if exit_day != day or at is None:
        return "on_time" if exit_day <= day else "late"
    if exit_at is None:
        return "unknown"
    return "on_time" if exit_at <= at else "late"


def _same_day_order_uncertain(day_events, active_lots):
    """Un retorno sin orden comprobable puede cambiar el primer cumplimiento."""
    outbound_lots = {event["lot_id"] for _, _, event in day_events if event["kind"] == "outbound"}
    candidate_lots = active_lots | outbound_lots
    returns = {
        at
        for _, at, event in day_events
        if event["kind"] == "return" and event["lot_id"] in candidate_lots
    }
    departures = {at for _, at, event in day_events if event["kind"] == "outbound"}
    return bool(returns and departures and (None in returns | departures or returns & departures))


def _candidate_movements(commitment, as_of, cancelled_at):
    """El alcance congelado y los sellos de evidencia delimitan la conciliación."""
    events = {}
    undated = []
    unknown = None
    lots = set(commitment["lot_ids"])
    all_lots_assigned = len(lots) == commitment["quantity"]
    first_day = _santiago_day(commitment["agreed_at"])
    last_day = _santiago_day(as_of)
    cancel_day = _santiago_day(cancelled_at) if cancelled_at else None
    for event in commitment["movements"]:
        if event["recorded_at"] > as_of:
            continue
        if all_lots_assigned and event["lot_id"] and event["lot_id"] not in lots:
            continue
        day, at = _day_and_time(event, "effective_date", "effective_at")
        if not day or not event["lot_id"]:
            undated.append(event)
            continue
        if not first_day <= day <= last_day or (at and not commitment["agreed_at"] <= at <= as_of):
            continue
        if (
            event["kind"] == "outbound"
            and cancel_day
            and (day > cancel_day or (at and at >= cancelled_at))
        ):
            continue
        identity = event["id"]
        if identity in events and events[identity][2] != event:
            unknown = "movement_evidence"
            continue
        events[identity] = (day, at, event)
    return (
        sorted(events.values(), key=lambda item: (item[0], item[1] is None, item[1])),
        undated,
        unknown,
    )


def _strictly_after(day, at, completion):
    exit_day, exit_at = completion
    return day > exit_day or (
        day == exit_day and at is not None and exit_at is not None and at > exit_at
    )


def _undated_evidence_reason(undated, events, completion):
    """Una devolución posterior con vínculo nativo acota una reentrega sin fecha."""
    if not undated:
        return None
    if completion is None:
        return "movement_evidence"
    returns_after = {
        event["id"]: event["lot_id"]
        for day, at, event in events
        if event["kind"] == "return" and _strictly_after(day, at, completion)
    }
    dated_ids = {event["id"] for _, _, event in events}
    if any(
        event["kind"] != "outbound"
        or not event["lot_id"]
        or event["id"] in dated_ids
        or returns_after.get(event.get("after_id")) != event["lot_id"]
        for event in undated
    ):
        return "movement_evidence"
    return None


def _first_completion(commitment, as_of, cancelled_at):
    """Una serie vuelve a estar disponible para acreditar salida tras su retorno."""
    events, undated, unknown = _candidate_movements(commitment, as_of, cancelled_at)
    if commitment.get("coverage_unknown"):
        unknown = "incomplete_coverage"
    active_lots = set()
    required_lots = set(commitment["lot_ids"])
    completion = None
    returned = False
    # Con fecha civil solo se conoce el día. Dejar su hora indeterminada
    # cuando una salida de esa precisión puede afectar la salida completa.
    for day, day_events in groupby(events, key=lambda item: item[0]):
        day_events = list(day_events)
        if completion is None and _same_day_order_uncertain(day_events, active_lots):
            return None, False, unknown or "ambiguous_movement_order"
        date_only = any(
            at is None and event["kind"] == "outbound"
            for _, at, event in day_events
            if event["lot_id"] not in active_lots
        )
        for _, at, event in day_events:
            if completion is not None:
                returned |= event["kind"] == "return" and event["lot_id"] in active_lots
            elif event["kind"] == "return":
                active_lots.discard(event["lot_id"])
            else:
                active_lots.add(event["lot_id"])
                if len(active_lots) >= commitment["quantity"] and required_lots <= active_lots:
                    if date_only and cancelled_at and day == _santiago_day(cancelled_at):
                        return None, False, unknown or "ambiguous_movement_order"
                    completion = (day, None if date_only else at)
    return completion, returned, unknown or _undated_evidence_reason(undated, events, completion)


def _last_reprogramming(changes, completion, as_of, cancelled_at):
    limit = cancelled_at or as_of
    if completion is not None:
        day, at = completion
        # La fecha sola no demuestra si un acuerdo del mismo día precede la salida.
        limit = min(at, limit) if at is not None else limit
    else:
        day, at = None, None
    return next(
        (
            change
            for change in reversed(changes)
            if change["kind"] == "reprogram"
            and change["agreed_at"] < limit
            and (day is None or at is not None or _santiago_day(change["agreed_at"]) < day)
        ),
        {},
    )


def _status(promise, completion, as_of, cancelled_at, unknown):
    if promise[0] is None:
        return "undefined", "missing_promise"
    if unknown:
        return "unknown", unknown
    if completion is None and cancelled_at:
        status = _deadline_result(promise, None, cancelled_at)
        return ("overdue", None) if status == "overdue" else ("cancelled", None)
    status = _deadline_result(promise, completion, as_of)
    return status, "missing_completion_time" if status == "unknown" else None


def _details(commitment, as_of):
    changes = sorted(
        (change for change in commitment["changes"] if _agreement_visible(change, as_of)),
        key=lambda change: change["agreed_at"],
    )
    cancelled_at = next(
        (change["agreed_at"] for change in changes if change["kind"] == "cancel"),
        None,
    )
    promise = _day_and_time(commitment, "promised_date", "promised_at")
    completion, returned, unknown = _first_completion(commitment, as_of, cancelled_at)
    status, reason = _status(promise, completion, as_of, cancelled_at, unknown)
    latest = _last_reprogramming(changes, completion, as_of, cancelled_at)
    secondary = _day_and_time(latest, "promised_date", "promised_at")
    secondary_status = (
        _status(secondary, completion, as_of, cancelled_at, unknown)[0] if latest else None
    )
    exit_day, exit_at = completion or (None, None)
    return {
        "id": commitment["id"],
        "status": status,
        "reason": reason,
        "secondary_status": secondary_status,
        "promised_date": promise[0],
        "promised_at": promise[1],
        "secondary_promised_date": secondary[0],
        "secondary_promised_at": secondary[1],
        "completed_date": exit_day,
        "completed_at": exit_at,
        "cancelled_at": cancelled_at,
        "returned_after_completion": returned,
    }


def _in_period(day, date_from, date_to):
    return day is not None and date_from <= day <= date_to


def _period_row(commitment, date_from, date_to, as_of):
    row = _details(commitment, as_of)
    row["in_due"] = _in_period(row["promised_date"], date_from, date_to)
    row["in_completed"] = _in_period(row["completed_date"], date_from, date_to)
    cancelled = row["cancelled_at"]
    if (
        row["in_due"]
        or row["in_completed"]
        or row["status"] in ("undefined", "unknown")
        or (cancelled is not None and _in_period(_santiago_day(cancelled), date_from, date_to))
    ):
        return {
            key: value.isoformat() if isinstance(value, date) else value
            for key, value in row.items()
        }
    return None


def _totals(rows, population):
    counts = dict.fromkeys(_STATUSES, 0)
    for row in rows:
        if row[population] and row["status"] != "pending":
            status = row["status"]
            counts["unknown" if status == "undefined" else status] += 1
    base = counts["on_time"] + counts["late"] + counts["overdue"]
    return {
        **counts,
        "denominator": base,
        "percentage": 100 * counts["on_time"] / base if base else None,
    }


def summarize_commitments(commitments, *, date_from, date_to, as_of):
    """Calcula dos cohortes inclusivas de Santiago con la evidencia al corte UTC.

    Los acuerdos y las salidas ya vienen autorizados y conciliados con el
    origen. Las fechas de consulta no reemplazan el corte de conocimiento.
    En una reentrega, `after_id` refiere a la línea de devolución vinculada
    por Inventario para la misma serie.
    """
    if date_from > date_to:
        raise ValueError("El inicio del período no puede ser posterior al fin")
    eligible = {}
    for commitment in commitments:
        if _agreement_visible(commitment, as_of):
            if eligible.setdefault(commitment["id"], commitment) != commitment:
                raise ValueError("Datos contradictorios para el mismo compromiso")
    rows = [
        row
        for commitment in eligible.values()
        if (row := _period_row(commitment, date_from, date_to, as_of)) is not None
    ]
    return {
        "due": _totals(rows, "in_due"),
        "completed": _totals(rows, "in_completed"),
        "rows": rows,
    }
