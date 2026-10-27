"""Unit coefficient, display class and Conflict Zone (GAME_RULES §3)."""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from engine import config
from engine.rounding import clamp


def vol12w(weekly_returns: Sequence[float]) -> float | None:
    """Sample standard deviation (n - 1) of the last VOL_WEEKS weekly returns, in %."""
    window = list(weekly_returns)[-config.VOL_WEEKS :]
    if len(window) < 2:
        return None
    return statistics.stdev(window)


def coefficient(vol: float | None) -> float:
    """clamp(REF_VOL / vol12w, COEF_MIN, COEF_MAX); no volatility data gives 1.0."""
    if vol is None:
        return 1.0
    if vol <= 0:
        return config.COEF_MAX
    return clamp(config.REF_VOL / vol, config.COEF_MIN, config.COEF_MAX)


def display_class(vol: float | None) -> str | None:
    if vol is None:
        return None
    for name, threshold in config.DISPLAY_CLASS_THRESHOLDS.items():
        if vol < threshold:
            return name
    return "kamikaze"


@dataclass(frozen=True, slots=True)
class ZoneCandidate:
    instrument_id: int
    earnings_next_week: bool
    market_cap: float | None
    last_week_return: float | None


def conflict_zone(candidates: Sequence[ZoneCandidate]) -> list[int]:
    """Earnings next week first (largest market cap first), then the largest absolute
    weekly moves; ties by instrument id."""
    earnings = sorted(
        (c for c in candidates if c.earnings_next_week),
        key=lambda c: (-(c.market_cap or 0.0), c.instrument_id),
    )
    movers = sorted(
        (c for c in candidates if not c.earnings_next_week),
        key=lambda c: (-abs(c.last_week_return or 0.0), c.instrument_id),
    )
    return [c.instrument_id for c in (earnings + movers)[: config.CONFLICT_ZONE_SIZE]]
