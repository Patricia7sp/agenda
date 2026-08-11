"""Cálculo de `reminder_at` (§3 da spec).

Regra: `reminder_at` é sempre derivado no backend, em UTC, a partir da data/hora
local do usuário. Recalcular em toda edição de data, hora ou lembrete.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def compute_reminder_at(
    scheduled_date: date,
    scheduled_time: time | None,
    reminder_offset_min: int | None,
    user_timezone: str,
) -> datetime | None:
    """Devolve o instante do lembrete em UTC, ou None se não houver lembrete.

    `reminder_offset_min`: None = sem lembrete · 0 = no horário · >0 = X min antes.
    """
    if reminder_offset_min is None or scheduled_time is None:
        return None

    tz = ZoneInfo(user_timezone)
    # O horário local é interpretado na timezone do usuário; o ZoneInfo resolve
    # DST (inclusive a virada de horário de verão) na conversão para UTC.
    local = datetime.combine(scheduled_date, scheduled_time, tzinfo=tz)
    return (local - timedelta(minutes=reminder_offset_min)).astimezone(timezone.utc)
