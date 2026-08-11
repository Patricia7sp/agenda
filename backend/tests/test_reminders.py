"""Conversão de horário local → UTC (critério de aceite do §9)."""

from datetime import date, time, timezone

from app.services.reminders import compute_reminder_at


def utc(dt):
    return dt.astimezone(timezone.utc)


def test_sem_offset_nao_gera_lembrete():
    assert compute_reminder_at(date(2026, 8, 10), time(17, 0), None, "America/Sao_Paulo") is None


def test_sem_horario_nao_gera_lembrete():
    assert compute_reminder_at(date(2026, 8, 10), None, 0, "America/Sao_Paulo") is None


def test_sao_paulo_utc_menos_3():
    r = utc(compute_reminder_at(date(2026, 8, 10), time(17, 0), 0, "America/Sao_Paulo"))
    assert (r.hour, r.minute, r.day) == (20, 0, 10)


def test_offset_atravessa_meia_noite():
    r = utc(compute_reminder_at(date(2026, 8, 10), time(0, 10), 30, "America/Sao_Paulo"))
    assert (r.day, r.hour, r.minute) == (10, 2, 40)  # 23:40 do dia 9 local = 02:40Z do dia 10


def test_horario_de_verao_antes_e_depois_da_virada():
    """Nova York muda para o horário de verão em 08/03/2026.

    O mesmo horário local (09:00) precisa cair em instantes UTC diferentes
    conforme o lado da virada — é isso que quebra quando se usa offset fixo.
    """
    antes = utc(compute_reminder_at(date(2026, 3, 7), time(9, 0), 0, "America/New_York"))
    depois = utc(compute_reminder_at(date(2026, 3, 9), time(9, 0), 0, "America/New_York"))

    assert antes.hour == 14   # EST, UTC-5
    assert depois.hour == 13  # EDT, UTC-4


def test_lisboa_no_verao():
    r = utc(compute_reminder_at(date(2026, 8, 10), time(17, 0), 0, "Europe/Lisbon"))
    assert r.hour == 16  # WEST, UTC+1
