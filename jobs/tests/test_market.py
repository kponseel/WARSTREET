"""Market week assembly with a fake provider."""

from __future__ import annotations

from datetime import date, timedelta

from engine import config
from engine.reference import DailyBar, Dividend
from jobs.market import CatalogueEntry, as_dicts, load_catalogue, reference_week, week_stats
from jobs.prices import Fundamentals, History

MONDAY = date(2026, 11, 9)


class FakeProvider:
    name = "fake"
    last_source = "fake"

    def __init__(self, missing: set[str] = frozenset()) -> None:  # type: ignore[assignment]
        self.missing = missing

    def history(self, ticker: str, start: date, end: date) -> History | None:
        if ticker in self.missing:
            return None
        history = History(ticker, "fake", "EUR")
        day, price = start, 100.0
        step = 1.0 + (sum(map(ord, ticker)) % 7) / 100  # a different trend per ticker
        while day <= end:
            if day.weekday() < 5:
                history.bars[day] = DailyBar(price, price * step)
                price *= step
            day += timedelta(days=1)
        history.dividends.append(Dividend(start + timedelta(days=1), 0.5))
        return history

    def live_price(self, ticker: str) -> float | None:
        return None

    def fundamentals(self, ticker: str) -> Fundamentals | None:
        if ticker.startswith("A"):
            return Fundamentals(float(len(ticker)), (MONDAY + timedelta(days=10),))
        return Fundamentals(None, ())


ENTRIES = [
    CatalogueEntry("AAPL", "Apple", "US", "XNYS", "USD", "magnificent_7"),
    CatalogueEntry("MC.PA", "LVMH", "EU", "XPAR", "EUR", "luxury_fashion"),
    CatalogueEntry("GONE", "Gone", "US", "XNYS", "USD", "x"),
]


def test_catalogue_loads_all_instruments() -> None:
    entries = load_catalogue()
    assert len(entries) == 100 and {e.region for e in entries} == {"EU", "US"}


def test_reference_week_reports_missing_and_dividends() -> None:
    rows = reference_week(FakeProvider(missing={"GONE"}), ENTRIES, MONDAY)
    assert [r.ticker for r in rows] == ["AAPL", "MC.PA", "GONE"]
    assert rows[0].p0 == 100.0 and rows[0].d1 == 0.5 and rows[0].missing == []
    assert rows[2].missing == ["p0", "p_mid", "p_end"] and rows[2].source is None
    assert as_dicts(rows)[0]["ticker"] == "AAPL"


def test_week_stats_and_conflict_zone() -> None:
    rows = week_stats(FakeProvider(missing={"GONE"}), ENTRIES, MONDAY + timedelta(days=7))
    aapl, lvmh, gone = rows
    assert aapl.earnings_date == MONDAY + timedelta(days=10) and "earnings" in aapl.weather
    assert lvmh.vol12w is not None and lvmh.display_class is not None
    assert gone.vol12w is None and gone.coef == 1.0 and gone.source is None
    assert sum(r.in_conflict_zone for r in rows) == min(len(rows), config.CONFLICT_ZONE_SIZE)
    assert as_dicts(rows)[0]["earnings_date"] == (MONDAY + timedelta(days=10)).isoformat()
