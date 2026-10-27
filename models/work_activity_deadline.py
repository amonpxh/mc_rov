from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WorkActivityDeadline(models.AbstractModel):
    """Fechas laborales de seguimiento, sin crear configuraciones ni modificar jornadas."""

    _name = "mc.rov.work.deadline"
    _description = "Cálculo de vencimientos laborales"

    @api.model
    def _working_date(
        self, calendar, company, started_at, days
    ):  # pylint: disable=too-many-locals
        """Cuenta fechas locales con trabajo efectivo, excluyendo el día del evento."""
        company.ensure_one()
        if (  # pylint: disable=too-many-boolean-expressions
            not calendar
            or calendar.flexible_hours
            or not calendar.tz
            or isinstance(days, bool)
            or not isinstance(days, int)
            or not 1 <= days <= 365
        ):
            raise ValidationError(_("Calendario o plazo laboral inválido."))
        started_at = fields.Datetime.to_datetime(started_at)
        if not started_at:
            raise ValidationError(_("Falta el instante de inicio de la etapa."))
        zone = pytz.timezone(calendar.tz)
        instant = started_at if started_at.tzinfo else pytz.utc.localize(started_at)
        first_day = instant.astimezone(zone).date() + timedelta(days=1)
        working_dates = set()
        # Los límites se localizan por fecha: no sumar 24 horas a través de DST.
        for offset in range(0, 366, 35):
            first = first_day + timedelta(days=offset)
            last = first_day + timedelta(days=min(offset + 35, 366))
            start = zone.localize(datetime.combine(first, time.min), is_dst=False)
            stop = zone.localize(datetime.combine(last, time.min), is_dst=False)
            intervals = calendar.with_context(employee_timezone=False)._work_intervals_batch(
                start,
                stop,
                resources=None,
                tz=zone,
                compute_leaves=True,
                domain=[
                    ("resource_id", "=", False),
                    ("company_id", "in", [False, company.id]),
                ],
            )[False]
            for begin, end, _attendance in intervals:
                day = begin.astimezone(zone).date()
                while day <= end.astimezone(zone).date():
                    left = zone.localize(datetime.combine(day, time.min), is_dst=False)
                    right = zone.localize(
                        datetime.combine(day + timedelta(days=1), time.min),
                        is_dst=False,
                    )
                    if first_day <= day < last and max(begin, left) < min(end, right):
                        working_dates.add(day)
                    day += timedelta(days=1)
            if len(working_dates) >= days:
                return sorted(working_dates)[days - 1]
        raise ValidationError(_("No hay suficientes días laborables en el próximo año."))
