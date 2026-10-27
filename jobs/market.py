"""Market data for one week, computed with engine/ from provider data.

- `reference_week`: P0, P_mid, P_end and dividends per instrument for a week.
- `week_stats`: what the Friday market job prepares for the NEXT week: vol12w, coef,
  display class, previous-week return, largest daily move, market cap, earnings date,
  weather and the Conflict Zone.

No database access here: the jobs of milestone 04 store the results.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path

from engine import config
from engine.calendar import segment_sessions
from engine.conflict_zone import ZoneCandidate, coefficient, conflict_zone, display_class, vol12w
from engine.models import Region
from engine.reference import instrument_week, max_abs_daily_move, weekly_returns
from engine.weather import weather_flags
from jobs.prices import PriceProvider

CATALOGUE = Path(__file__).resolve().parents[1] / "data" / "instruments.csv"
HISTORY_WEEKS = config.VOL_WEEKS + 2  # enough weekly closes for VOL_WEEKS returns


@dataclass(frozen=True, slots=True)
class CatalogueEntry:
    ticker: str
    name: str
    region: Region
    calendar_mic: str
    currency: str
    sector: str


def load_catalogue(path: Path = CATALOGUE) -> list[CatalogueEntry]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [CatalogueEntry(**row) for row in csv.DictReader(handle)]  # type: ignore[arg-type]


@dataclass(slots=True)
class ReferenceRow:
    ticker: str
    p0: float | None
    p_mid: float | None
    p_end: float | None
    d1: float
    d2: float
    source: str | None
    missing: list[str] = field(default_factory=list)


def reference_week(
    provider: PriceProvider, catalogue: list[CatalogueEntry], monday: date
) -> list[ReferenceRow]:
    rows = []
    for index, entry in enumerate(catalogue, start=1):
        sessions = segment_sessions(entry.calendar_mic, monday)
        history = provider.history(entry.ticker, monday, monday + timedelta(days=4))
        source = getattr(provider, "last_source", provider.name) if history else None
        week = instrument_week(
            index,
            entry.region,
            sessions,
            history.bars if history else {},
            history.dividends if history else (),
        )
        missing = [k for k in ("p0", "p_mid", "p_end") if getattr(week, k) is None]
        rows.append(
            ReferenceRow(
                entry.ticker, week.p0, week.p_mid, week.p_end, week.d1, week.d2, source, missing
            )
        )
    return rows


@dataclass(slots=True)
class StatsRow:
    ticker: str
    vol12w: float | None
    coef: float
    display_class: str | None
    prev_week_return: float | None
    max_abs_daily_move_prev: float | None
    market_cap: float | None
    earnings_date: date | None
    weather: list[str]
    in_conflict_zone: bool = False
    source: str | None = None


def week_stats(
    provider: PriceProvider, catalogue: list[CatalogueEntry], next_monday: date
) -> list[StatsRow]:
    """Stats for the week starting `next_monday`, from data up to the Friday before."""
    friday = next_monday - timedelta(days=3)
    start = friday - timedelta(weeks=HISTORY_WEEKS)
    next_friday = next_monday + timedelta(days=4)
    rows: list[StatsRow] = []
    for entry in catalogue:
        history = provider.history(entry.ticker, start, friday)
        source = getattr(provider, "last_source", provider.name) if history else None
        closes = history.closes if history else {}
        returns = weekly_returns(closes)
        vol = vol12w(returns)
        prev = returns[-1] if returns else None
        move = max_abs_daily_move(closes, friday - timedelta(days=4), friday)
        fundamentals = provider.fundamentals(entry.ticker)
        earnings = None
        if fundamentals:
            upcoming = [d for d in fundamentals.earnings_dates if next_monday <= d <= next_friday]
            earnings = min(upcoming) if upcoming else None
        rows.append(
            StatsRow(
                ticker=entry.ticker,
                vol12w=vol,
                coef=coefficient(vol),
                display_class=display_class(vol),
                prev_week_return=prev,
                max_abs_daily_move_prev=move,
                market_cap=fundamentals.market_cap if fundamentals else None,
                earnings_date=earnings,
                weather=weather_flags(prev, earnings is not None, move),
                source=source,
            )
        )
    zone = set(
        conflict_zone(
            [
                ZoneCandidate(i, r.earnings_date is not None, r.market_cap, r.prev_week_return)
                for i, r in enumerate(rows)
            ]
        )
    )
    for index, row in enumerate(rows):
        row.in_conflict_zone = index in zone
    return rows


def as_dicts(rows: list[ReferenceRow] | list[StatsRow]) -> list[dict[str, object]]:
    return [
        {k: (v.isoformat() if isinstance(v, date) else v) for k, v in asdict(row).items()}
        for row in rows
    ]
