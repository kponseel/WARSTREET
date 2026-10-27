"""Reference prices from daily bars."""

from datetime import date

import pytest

from engine.calendar import SegmentSessions
from engine.reference import (
    DailyBar,
    Dividend,
    instrument_week,
    max_abs_daily_move,
    weekly_closes,
    weekly_returns,
)

S = SegmentSessions(date(2026, 11, 9), date(2026, 11, 12), date(2026, 11, 13))
BARS = {
    date(2026, 11, 9): DailyBar(100, 101),
    date(2026, 11, 10): DailyBar(101, 102),
    date(2026, 11, 11): DailyBar(102, 103),
    date(2026, 11, 12): DailyBar(104, 105),
    date(2026, 11, 13): DailyBar(105, 106),
}


def test_reference_prices_and_dividends() -> None:
    dividends = [
        Dividend(date(2026, 11, 10), 1.0),
        Dividend(date(2026, 11, 13), 0.5),
        Dividend(date(2026, 11, 9), 9.0),
    ]
    week = instrument_week(7, "EU", S, BARS, dividends, coef=1.5, prev_week_return=-2.0)
    assert (week.p0, week.p_mid, week.p_end) == (100, 104, 106)
    assert (week.d1, week.d2) == (1.0, 0.5)  # the Monday ex-date is already inside P0
    assert (week.coef, week.prev_week_return, week.k1, week.k2) == (1.5, -2.0, 1.0, 1.0)


def test_halt_uses_the_last_available_close() -> None:
    bars = {**BARS, date(2026, 11, 13): DailyBar(None, None)}
    assert instrument_week(7, "EU", S, bars).p_end == 105
    bars = {d: b for d, b in BARS.items() if d < date(2026, 11, 12)}
    week = instrument_week(7, "EU", S, bars)
    assert week.p_mid is None and week.p_end is None  # nothing in S2: flagged as missing


def test_no_session_at_all() -> None:
    week = instrument_week(7, "EU", SegmentSessions(None, None, None), BARS)
    assert (week.p0, week.p_mid, week.p_end) == (None, None, None)


CLOSES = {
    date(2026, 10, 30): 100.0,
    date(2026, 11, 2): 101.0,
    date(2026, 11, 6): 110.0,
    date(2026, 11, 9): 99.0,
    date(2026, 11, 13): 99.0,
}


def test_weekly_closes_and_returns() -> None:
    assert weekly_closes(CLOSES) == [
        (date(2026, 10, 30), 100.0),
        (date(2026, 11, 6), 110.0),
        (date(2026, 11, 13), 99.0),
    ]
    assert weekly_returns(CLOSES) == pytest.approx([10.0, -10.0])


def test_max_abs_daily_move() -> None:
    assert max_abs_daily_move(CLOSES, date(2026, 11, 9), date(2026, 11, 13)) == pytest.approx(10.0)
    assert max_abs_daily_move(CLOSES, date(2027, 1, 1), date(2027, 1, 8)) is None
