"""Agrega hechos acreditados; no confunde registros, visitas y equipos."""

from collections import defaultdict
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

MILESTONES = ("manufactured", "accepted", "released", "outbound", "reversed")


def local_day(value):
    """Los sellos UTC se agrupan por día de Santiago, no por día del servidor."""
    if not value:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(value, datetime):
        return (
            value.replace(tzinfo=value.tzinfo or timezone.utc)
            .astimezone(ZoneInfo("America/Santiago"))
            .date()
        )
    if isinstance(value, date):
        return value
    raise ValueError("Fecha de evidencia no válida")


def period_bounds(date_from=False, date_to=False):
    """Valida límites inclusivos; no reemplaza una fecha ausente por hoy."""
    start = date.fromisoformat(date_from) if date_from else None
    end = date.fromisoformat(date_to) if date_to else None
    if start and end and start > end:
        raise ValueError("El inicio no puede ser posterior al fin")
    return start, end


def first_events(events):
    """Una identidad conserva el primer sello aunque cambie el orden de lectura."""
    earliest = {}
    for event in events:
        key = event["kind"], event["identity"]
        stamp = event.get("at") or "9999"
        if key not in earliest or stamp < (earliest[key].get("at") or "9999"):
            earliest[key] = event
    return earliest.values()


def summarize_events(events, date_from=False, date_to=False, revision="all"):
    """Cuenta una identidad por hito y conserva desconocidos fuera del numerador."""
    bounds = period_bounds(date_from, date_to)
    if revision != "all" and not isinstance(revision, (list, tuple, set)):
        raise ValueError("La revisión debe resolverse por configuración")
    report = {
        "repair": {"visits": 0, "equipment": 0, "unknown_revision": 0},
        "manufacturing": dict.fromkeys((*MILESTONES, "unknown_revision"), 0),
        "unknown_date": 0,
    }
    lots = set()
    for event in first_events(events):
        kind = event["kind"]
        if kind not in ("repair_done", *MILESTONES):
            continue
        day = local_day(event.get("at"))
        if day is None:
            report["unknown_date"] += 1
            continue
        if (bounds[0] and day < bounds[0]) or (bounds[1] and day > bounds[1]):
            continue
        target = report["repair" if kind == "repair_done" else "manufacturing"]
        design = event.get("revision_key")
        if not design:
            target["unknown_revision"] += 1
            if revision != "all":
                continue
        elif revision != "all" and design not in revision:
            continue
        if kind == "repair_done":
            target["visits"] += 1
            if event.get("lot_id"):
                lots.add(event["lot_id"])
        else:
            target[kind] += 1
    report["repair"]["equipment"] = len(lots)
    return report


def _pareto_groups(observations, dimension, unit):
    """Conserva miembros distintos por categoría y ausencia de unidad."""
    groups, labels, seen = defaultdict(set), {}, set()
    missing_unit = 0
    for row in observations:
        identity = row["identity"]
        if identity in seen:
            continue
        seen.add(identity)
        key = row.get(dimension + "_id") or 0
        labels[key] = row.get(dimension + "_label") or "Sin clasificar"
        member = (
            identity
            if unit == "observations"
            else row.get("visit_id" if unit == "visits" else "lot_id")
        )
        if not member:
            missing_unit += 1
            continue
        groups[key].add(member)
    return groups, labels, missing_unit


def pareto(observations, dimension="finding", unit="observations", limit=10):
    """El denominador incluye Sin clasificar y Otros; jamás inventa incidentes."""
    if dimension not in ("finding", "component") or unit not in (
        "observations",
        "visits",
        "equipment",
    ):
        raise ValueError("Unidad o dimensión de Pareto no válida")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("El límite debe ser un entero positivo")
    groups, labels, missing_unit = _pareto_groups(observations, dimension, unit)
    counts = sorted(
        ((key, len(members)) for key, members in groups.items()),
        key=lambda item: (-item[1], str(item[0])),
    )
    total = sum(count for _key, count in counts)
    rows = [{"key": key, "label": labels[key], "count": count} for key, count in counts[:limit]]
    if len(counts) > limit:
        rows.append({"key": "other", "label": "Otros", "count": sum(n for _, n in counts[limit:])})
    accumulated = 0
    for row in rows:
        accumulated += row["count"]
        row.update(
            percent=round(row["count"] * 100 / total, 2),
            cumulative_percent=round(accumulated * 100 / total, 2),
        )
    return {
        "rows": rows,
        "total": total,
        "unit": unit,
        "unclassified": len(groups.get(0, set())),
        "missing_unit": missing_unit,
        "denominator": "category_memberships" if unit != "observations" else "observations",
    }
