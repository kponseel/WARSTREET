"""Exchange calendars and phase timestamps (GAME_RULES §2, §12)."""

from datetime import UTC, date, datetime

import pytest

from engine.calendar import (
    MICS,
    SegmentSessions,
    dividend_segment,
    first_open,
    first_open_from_thursday,
    last_close,
    local_instant,
    phase_timestamps,
    segment_sessions,
    week_monday,
    week_sessions,
)


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


def test_every_catalogue_exchange_is_known() -> None:
    for mic in MICS:
        assert len(week_sessions(mic, date(2026, 11, 9))) == 5


def test_normal_week_winter() -> None:
    monday = date(2026, 11, 9)  # Paris UTC+1, New York UTC-5
    assert first_open("XPAR", monday) == utc(2026, 11, 9, 8, 0)
    assert first_open("XNYS", monday) == utc(2026, 11, 9, 14, 30)
    assert first_open_from_thursday("XETR", monday) == utc(2026, 11, 12, 8, 0)
    assert last_close("XNYS", monday) == utc(2026, 11, 13, 21, 0)
    ts = phase_timestamps(monday)
    assert ts.lock_at == utc(2026, 11, 8, 22, 59, 59)
    assert ts.resupply_opens_at == utc(2026, 11, 11, 21, 5)
    assert ts.resupply_closes_at == utc(2026, 11, 12, 7, 59, 59)
    assert ts.debrief_at == utc(2026, 11, 13, 21, 30)


def test_dst_mismatch_week() -> None:
    monday = date(2026, 10, 26)  # Europe already on winter time, the US not yet
    assert first_open("XPAR", monday) == utc(2026, 10, 26, 8, 0)
    assert first_open("XNYS", monday) == utc(2026, 10, 26, 13, 30)  # 14:30 in Paris
    ts = phase_timestamps(monday)
    assert ts.lock_at == utc(2026, 10, 25, 22, 59, 59)
    assert ts.resupply_opens_at == utc(2026, 10, 28, 20, 5)  # 21:05 in Paris
    assert ts.debrief_at == utc(2026, 10, 30, 20, 30)


def test_summer_week() -> None:
    ts = phase_timestamps(date(2026, 6, 8))  # Paris UTC+2, New York UTC-4
    assert ts.lock_at == utc(2026, 6, 7, 21, 59, 59)
    assert ts.resupply_closes_at == utc(2026, 6, 11, 6, 59, 59)
    assert ts.debrief_at == utc(2026, 6, 12, 20, 30)


def test_thanksgiving_and_half_day_friday() -> None:
    monday = date(2026, 11, 23)
    sessions = segment_sessions("XNYS", monday)
    assert sessions == SegmentSessions(date(2026, 11, 23), date(2026, 11, 27), date(2026, 11, 27))
    assert first_open_from_thursday("XNYS", monday) == utc(2026, 11, 27, 14, 30)
    assert phase_timestamps(monday).debrief_at == utc(2026, 11, 27, 18, 30)  # 13:00 ET close
    assert segment_sessions("XPAR", monday).p_mid == date(2026, 11, 26)  # Europe trades


def test_may_first_in_europe() -> None:
    monday = date(2026, 4, 27)  # Friday 1 May 2026
    assert segment_sessions("XPAR", monday).p_end == date(2026, 4, 30)
    assert segment_sessions("XETR", monday).p_end == date(2026, 4, 30)
    assert segment_sessions("XNYS", monday).p_end == date(2026, 5, 1)


def test_easter_monday() -> None:
    monday = date(2026, 4, 6)
    assert segment_sessions("XPAR", monday).p0 == date(2026, 4, 7)  # P0 = first open
    assert segment_sessions("XNYS", monday).p0 == date(2026, 4, 6)


def test_christmas_friday_everything_closed() -> None:
    monday = date(2026, 12, 21)
    for mic in MICS:
        assert date(2026, 12, 25) not in week_sessions(mic, monday)
    assert last_close("XNYS", monday) == utc(2026, 12, 24, 18, 0)  # US half day on the 24th
    assert phase_timestamps(monday).debrief_at == utc(2026, 12, 24, 18, 30)


def test_independence_day_observed_friday() -> None:
    monday = date(2026, 6, 29)
    assert segment_sessions("XNYS", monday).p_end == date(2026, 7, 2)
    assert segment_sessions("XPAR", monday).p_end == date(2026, 7, 3)
    assert phase_timestamps(monday).debrief_at == utc(2026, 7, 2, 20, 30)


def test_us_holiday_on_wednesday_moves_resupply_opening() -> None:
    monday = date(2024, 6, 17)  # Juneteenth, Wednesday 19 June 2024: US closed
    assert date(2024, 6, 19) not in week_sessions("XNYS", monday)
    assert phase_timestamps(monday).resupply_opens_at == utc(2024, 6, 18, 20, 5)  # Tuesday close
    monday = date(2025, 12, 29)  # New Year's Day 2026 is a Thursday: Wednesday still trades
    assert phase_timestamps(monday).resupply_opens_at == utc(2025, 12, 31, 21, 5)


def test_week_without_us_session_before_thursday_uses_the_fallback(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import engine.calendar as cal

    monkeypatch.setattr(cal, "week_sessions", lambda mic, monday: [date(2026, 11, 13)])
    ts = cal.phase_timestamps(date(2026, 11, 9))
    assert ts.resupply_opens_at == utc(2026, 11, 11, 21, 0)  # Wednesday 22:00 Paris
    monkeypatch.setattr(cal, "week_sessions", lambda mic, monday: [])
    with pytest.raises(ValueError, match="no XNYS session"):
        cal.phase_timestamps(date(2026, 11, 9))


def test_mondays_only() -> None:
    with pytest.raises(ValueError):
        phase_timestamps(date(2026, 11, 10))


S = SegmentSessions(date(2026, 11, 9), date(2026, 11, 12), date(2026, 11, 13))


@pytest.mark.parametrize(
    ("ex_date", "segment"),
    [
        (date(2026, 11, 9), None),  # first session of S1: already inside P0
        (date(2026, 11, 10), "s1"),
        (date(2026, 11, 12), "s1"),  # last session of S1 (P_mid open is ex)
        (date(2026, 11, 13), "s2"),  # last session of S2
        (date(2026, 11, 16), None),
    ],
)
def test_dividend_segment(ex_date: date, segment: str | None) -> None:
    assert dividend_segment(S, ex_date) == segment


def test_dividend_segment_without_sessions() -> None:
    assert dividend_segment(SegmentSessions(None, None, None), date(2026, 11, 10)) is None
    no_thursday = SegmentSessions(date(2026, 11, 9), None, date(2026, 11, 11))
    assert dividend_segment(no_thursday, date(2026, 11, 11)) == "s1"
    assert dividend_segment(no_thursday, date(2026, 11, 9)) is None


def test_empty_week_has_no_open_or_close(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import engine.calendar as cal

    monkeypatch.setattr(cal, "week_sessions", lambda mic, monday: [])
    assert cal.first_open("XPAR", date(2026, 11, 9)) is None
    assert cal.first_open_from_thursday("XPAR", date(2026, 11, 9)) is None
    assert cal.last_close("XPAR", date(2026, 11, 9)) is None


def test_local_instant_and_week_monday() -> None:
    assert local_instant(date(2026, 3, 29), "12:00:00") == utc(2026, 3, 29, 10, 0)  # CEST
    assert week_monday(utc(2026, 11, 8, 23, 30)) == date(2026, 11, 9)  # Monday 00:30 Paris
    assert week_monday(utc(2026, 11, 8, 22, 0)) == date(2026, 11, 2)  # Sunday 23:00 Paris
