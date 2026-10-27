"""Segment and weekly returns in percent (GAME_RULES §2, §8)."""

from __future__ import annotations

from engine.models import InstrumentWeek


def segment_return(
    start: float | None, end: float | None, dividend: float = 0.0, split: float = 1.0
) -> float | None:
    """((end + dividend) * split / start - 1) * 100, or None when a price is missing."""
    if start is None or end is None or start <= 0:
        return None
    return ((end + dividend) * split / start - 1.0) * 100.0


def s1_return(week: InstrumentWeek) -> float | None:
    return segment_return(week.p0, week.p_mid, week.d1, week.k1)


def s2_return(week: InstrumentWeek) -> float | None:
    return segment_return(week.p_mid, week.p_end, week.d2, week.k2)


def weekly_return(week: InstrumentWeek) -> float | None:
    """((P_end + D2) * k2 * k1 + D1 * k1) / P0 - 1, in %; None without P0 or P_end."""
    if week.p0 is None or week.p_end is None or week.p0 <= 0:
        return None
    end_value = (week.p_end + week.d2) * week.k2 * week.k1 + week.d1 * week.k1
    return (end_value / week.p0 - 1.0) * 100.0
