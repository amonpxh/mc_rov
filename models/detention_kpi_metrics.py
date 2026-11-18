"""F2 puro: tiempo de detenciones registradas, sin inferir disponibilidad ni HH."""

from collections import defaultdict
from datetime import datetime, timezone


CAUSES = (
    "materials",
    "client",
    "engineering",
    "documentation",
    "resources",
    "external",
    "other",
)
SOURCE_MODELS = ("repair.order", "mrp.production")


def _instant(value):
    """Odoo entrega UTC naive; una fecha civil sola no acredita un instante físico."""
    if isinstance(value, str):
        if "T" not in value and " " not in value:
            raise ValueError("Se requiere fecha y hora, no solo una fecha civil")
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("Instante de detención inválido") from error
    if not isinstance(value, datetime):
        raise ValueError("Se requiere un instante de detención")
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _order_key(value):
    if not isinstance(value, tuple) or len(value) != 2:
        raise ValueError("La identidad requiere modelo e ID de orden")
    if (
        value[0] not in SOURCE_MODELS
        or isinstance(value[1], bool)
        or not isinstance(value[1], int)
        or value[1] < 1
    ):
        raise ValueError("La identidad requiere modelo e ID de orden")
    return value


def _interval_key(value):
    if isinstance(value, bool) or not (
        (isinstance(value, int) and value > 0) or (isinstance(value, str) and value.strip())
    ):
        raise ValueError("Falta identidad de la evidencia de detención")
    return value


def _union_seconds(intervals):
    """El solape se une dentro de una orden; nunca se une entre dos órdenes."""
    seconds = 0.0
    current = None
    for start, end in sorted(intervals):
        if current is None:
            current = (start, end)
        elif start <= current[1]:
            current = (current[0], max(current[1], end))
        else:
            seconds += (current[1] - current[0]).total_seconds()
            current = (start, end)
    if current is not None:
        seconds += (current[1] - current[0]).total_seconds()
    return seconds


def _orders_at_cutoff(orders):
    sources = {}
    for order in orders:
        identity = _order_key(order.get("identity"))
        if identity in sources:
            raise ValueError("Orden duplicada en la población")
        if not isinstance(order.get("open_at_cutoff"), bool):
            raise ValueError("El estado al corte debe ser explícito")
        sources[identity] = order["open_at_cutoff"]
    return sources


def _validated_intervals(intervals, sources, cutoff):
    seen = {}
    for row in intervals:
        identity = _interval_key(row.get("identity"))
        if identity in seen:
            if row != seen[identity]:
                raise ValueError("Copias contradictorias de la misma detención")
            continue
        seen[identity] = row
        order = _order_key(row.get("order"))
        if order not in sources:
            raise ValueError("La detención no pertenece a la población autorizada")
        cause = row.get("cause")
        if cause not in CAUSES:
            raise ValueError("Causa de detención desconocida")
        start = _instant(row["start"]) if row.get("start") is not None else None
        end = _instant(row["end"]) if row.get("end") is not None else None
        if start is not None and end is not None and end < start:
            raise ValueError("La detención termina antes de comenzar")
        if not sources[order] and (end is None or end > cutoff):
            raise ValueError("Una orden cerrada al corte conserva detención abierta")
        yield order, cause, start, end


class _EvidenceTotals:
    """Acumuladores internos del cálculo; nunca se reutilizan entre consultas."""

    def __init__(self):
        self.by_order = defaultdict(list)
        self.by_cause = {cause: defaultdict(list) for cause in CAUSES}
        self.unknown_by_cause = dict.fromkeys(CAUSES, 0)
        self.count_by_cause = dict.fromkeys(CAUSES, 0)
        self.unknown_by_order = defaultdict(int)
        self.stopped = set()
        self.recorded_orders = set()


def summarize_detentions(orders, intervals, start, end, cutoff):
    """Agrega hechos ya autorizados y estados explícitos al corte suministrado.

    El adaptador resuelve la población y sus permisos; esta función no conoce
    usuarios, cron ni el reloj global. Período [start,end); duración hasta cutoff.
    open_at_cutoff exige evidencia de ese corte: no reconstruye historia desde
    el estado actual. El porcentaje expresa detenciones registradas actuales,
    no ausencia demostrada de otras detenciones ni una tasa de disponibilidad.
    La cobertura y las duraciones desconocidas describen toda la evidencia
    suministrada de la población, no una tasa de cobertura del período elegido.
    """
    start, end, cutoff = _instant(start), _instant(end), _instant(cutoff)
    if start >= end:
        raise ValueError("El período debe tener inicio anterior al fin")
    stop = min(end, cutoff)
    sources = _orders_at_cutoff(orders)
    totals = _EvidenceTotals()
    for order, cause, began, ended in _validated_intervals(intervals, sources, cutoff):
        if began is None:
            totals.unknown_by_cause[cause] += 1
            totals.unknown_by_order[order] += 1
            totals.recorded_orders.add(order)
            continue
        if began > cutoff:
            continue
        totals.recorded_orders.add(order)
        if sources[order] and (ended is None or ended > cutoff):
            totals.stopped.add(order)
        left, right = max(start, began), min(stop, ended or cutoff)
        if left >= right:
            continue
        totals.by_order[order].append((left, right))
        totals.by_cause[cause][order].append((left, right))
        totals.count_by_cause[cause] += 1
    open_count = sum(sources.values())
    return {
        "open_orders": open_count,
        "registered_stopped_orders": len(totals.stopped),
        "registered_stopped_percent": (
            100 * len(totals.stopped) / open_count if open_count else None
        ),
        "recorded_seconds": sum(_union_seconds(rows) for rows in totals.by_order.values()),
        "recorded_interval_count": sum(totals.count_by_cause.values()),
        "unknown_duration_intervals": sum(totals.unknown_by_cause.values()),
        "orders_without_recorded_intervals": len(sources.keys() - totals.recorded_orders),
        "coverage_basis": "recorded_intervals_only",
        "coverage_scope": "population_history",
        "duration_unit": "order_seconds",
        "causes_additive": False,
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "cutoff": cutoff.isoformat(),
        },
        "by_cause": {
            cause: {
                "recorded_seconds": sum(_union_seconds(rows) for rows in groups.values()),
                "recorded_interval_count": totals.count_by_cause[cause],
                "unknown_duration_intervals": totals.unknown_by_cause[cause],
            }
            for cause, groups in totals.by_cause.items()
        },
        "by_order": [
            {
                "identity": identity,
                "recorded_seconds": _union_seconds(totals.by_order[identity]),
                "registered_stopped": identity in totals.stopped,
                "unknown_duration_intervals": totals.unknown_by_order[identity],
            }
            for identity in sorted(sources)
        ],
    }
