"""Duración en días calendario de Santiago para visitas con salida acreditada."""

from datetime import datetime
from math import ceil
from statistics import median

if __package__:
    from .production_kpi_metrics import local_day
else:
    from production_kpi_metrics import local_day


def summarize(pairs):
    """Separa las visitas sin recepción y cronologías incompatibles de la duración."""
    days = []
    missing = invalid = 0
    for arrival, departure in pairs:
        if arrival is None:
            missing += 1
            continue
        end = local_day(departure) if isinstance(departure, datetime) else departure
        elapsed = (end - local_day(arrival)).days
        if elapsed < 0 or (isinstance(departure, datetime) and departure < arrival):
            invalid += 1
            continue
        days.append(elapsed)
    days.sort()
    bands = [(0, 2), (3, 7), (8, 14), (15, 30), (31, None)]
    return {
        "samples": len(days),
        "missing_arrival": missing,
        "invalid_chronology": invalid,
        "median_days": median(days) if days else None,
        "p80_days": days[ceil(0.8 * len(days)) - 1] if len(days) >= 10 else None,
        "distribution": [
            {
                "minimum": low,
                "maximum": high,
                "count": sum(low <= day and (high is None or day <= high) for day in days),
            }
            for low, high in bands
        ],
    }
