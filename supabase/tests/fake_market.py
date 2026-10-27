"""A deterministic price provider for job tests (no network)."""

from __future__ import annotations

from datetime import date, timedelta

from engine.reference import DailyBar, Dividend
from jobs.prices import Fundamentals, History


class FakeMarket:
    name = "fake"
    last_source = "fake"

    def __init__(self, earnings: dict[str, date] | None = None) -> None:
        self.earnings = earnings or {}
        self.calls = 0

    @staticmethod
    def _drift(ticker: str) -> float:
        return ((sum(map(ord, ticker)) % 11) - 5) / 1000  # -0.5 % .. +0.5 % a day

    def history(self, ticker: str, start: date, end: date) -> History | None:
        self.calls += 1
        history = History(ticker, self.name, "EUR")
        day, price = date(2026, 1, 1), 100.0
        while day <= end:
            if day.weekday() < 5:
                opened = price * (1 + self._drift(ticker) / 2)
                price = price * (1 + self._drift(ticker)) * (1.02 if day.day % 7 == 0 else 1.0)
                if day >= start:
                    history.bars[day] = DailyBar(round(opened, 4), round(price, 4))
            day += timedelta(days=1)
        if ticker == "PG":
            history.dividends.append(Dividend(date(2026, 11, 13), 1.0))
        return history

    def live_price(self, ticker: str) -> float | None:
        return 100.0 * (1 + self._drift(ticker) * 50)

    def fundamentals(self, ticker: str) -> Fundamentals | None:
        when = self.earnings.get(ticker)
        return Fundamentals(float(sum(map(ord, ticker))), (when,) if when else ())
