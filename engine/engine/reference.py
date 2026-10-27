"""Reference prices of a week from daily bars (GAME_RULES §2, §12). Pure: the jobs fetch
the bars, this module only reads them.

Bars are expected from ONE provider fetch, so every price and dividend is on the same
share basis (Yahoo adjusts past prices for splits, not for dividends, when
`auto_adjust=False`): split ratios are then 1. Prices captured at different times are the
jobs' concern (milestone 04).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from itertools import pairwise

from engine.calendar import SegmentSessions, dividend_segment
from engine.models import InstrumentWeek, Region


@dataclass(frozen=True, slots=True)
class DailyBar:
    open: float | None
    close: float | None


@dataclass(frozen=True, slots=True)
class Dividend:
    ex_date: date
    amount: float


def _last_close(bars: Mapping[date, DailyBar], start: date, end: date) -> float | None:
    """Close of the last session in [start, end] with data: a halt or a delisting mid-week
    uses the last available price."""
    for day in sorted((d for d in bars if start <= d <= end), reverse=True):
        if bars[day].close is not None:
            return bars[day].close
    return None


def instrument_week(
    instrument_id: int,
    region: Region,
    sessions: SegmentSessions,
    bars: Mapping[date, DailyBar],
    dividends: Sequence[Dividend] = (),
    *,
    coef: float = 1.0,
    prev_week_return: float | None = None,
) -> InstrumentWeek:
    p0 = bars[sessions.p0].open if sessions.p0 and sessions.p0 in bars else None
    p_mid = bars[sessions.p_mid].open if sessions.p_mid and sessions.p_mid in bars else None
    p_end = None
    if sessions.p_end is not None:
        start = sessions.p_mid or sessions.p0 or sessions.p_end
        p_end = _last_close(bars, start, sessions.p_end)
    d1 = sum(d.amount for d in dividends if dividend_segment(sessions, d.ex_date) == "s1")
    d2 = sum(d.amount for d in dividends if dividend_segment(sessions, d.ex_date) == "s2")
    return InstrumentWeek(
        instrument_id=instrument_id,
        region=region,
        p0=p0,
        p_mid=p_mid,
        p_end=p_end,
        d1=d1,
        d2=d2,
        coef=coef,
        prev_week_return=prev_week_return,
    )


def weekly_closes(closes: Mapping[date, float]) -> list[tuple[date, float]]:
    """The last close of each ISO week, oldest first."""
    last: dict[tuple[int, int], tuple[date, float]] = {}
    for day in sorted(closes):
        year, week, _ = day.isocalendar()
        last[(year, week)] = (day, closes[day])
    return [last[k] for k in sorted(last)]


def weekly_returns(closes: Mapping[date, float]) -> list[float]:
    """Close-to-close weekly returns in %, oldest first (input for vol12w)."""
    points = weekly_closes(closes)
    return [
        (later / earlier - 1.0) * 100.0
        for (_, earlier), (_, later) in pairwise(points)
        if earlier > 0
    ]


def max_abs_daily_move(closes: Mapping[date, float], start: date, end: date) -> float | None:
    """Largest absolute close-to-close daily move in % for sessions in [start, end]."""
    days = sorted(closes)
    moves = [
        abs(closes[b] / closes[a] - 1.0) * 100.0
        for a, b in pairwise(days)
        if start <= b <= end and closes[a] > 0
    ]
    return max(moves) if moves else None
