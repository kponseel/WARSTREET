"""Price providers without network: fake HTTP session and fake yfinance module."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pandas as pd
import pytest
import requests

from engine.reference import DailyBar, Dividend
from jobs.prices import (
    FallbackProvider,
    Fundamentals,
    History,
    ProviderError,
    Split,
    YahooChartProvider,
    YFinanceProvider,
    default_provider,
    with_retries,
)


def ts(day: date, hour: int = 8) -> int:
    return int(datetime(day.year, day.month, day.day, hour, tzinfo=UTC).timestamp())


class FakeResponse:
    def __init__(self, status: int, payload: Any = None) -> None:
        self.status_code, self._payload = status, payload

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, *responses: Any) -> None:
        self.responses, self.calls = list(responses), []

    def get(self, url: str, **kwargs: Any) -> Any:
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


CHART = {
    "chart": {
        "result": [
            {
                "meta": {"currency": "EUR", "gmtoffset": 3600, "regularMarketPrice": 101.5},
                "timestamp": [
                    ts(date(2026, 11, 9)),
                    ts(date(2026, 11, 10)),
                    ts(date(2026, 11, 16)),
                ],
                "indicators": {"quote": [{"open": [100, None, 9], "close": [101, 102, 9]}]},
                "events": {
                    "dividends": {
                        "x": {"date": ts(date(2026, 11, 10)), "amount": 1.25},
                        "y": {"date": ts(date(2026, 12, 1)), "amount": 9},
                    },
                    "splits": {
                        "s": {"date": ts(date(2026, 11, 9)), "numerator": 2, "denominator": 1}
                    },
                },
            }
        ]
    }
}


def test_chart_history_parses_bars_dividends_and_splits() -> None:
    session = FakeSession(FakeResponse(200, CHART))
    history = YahooChartProvider(session).history("MC.PA", date(2026, 11, 9), date(2026, 11, 13))
    assert history is not None and history.currency == "EUR" and history.source == "yahoo-chart"
    assert history.bars == {
        date(2026, 11, 9): DailyBar(100, 101),
        date(2026, 11, 10): DailyBar(None, 102),
    }
    assert history.dividends == [Dividend(date(2026, 11, 10), 1.25)]
    assert history.splits == [Split(date(2026, 11, 9), 2.0)]
    assert history.closes == {date(2026, 11, 9): 101, date(2026, 11, 10): 102}
    assert session.calls[0][1]["params"]["events"] == "div,splits"


def test_chart_errors() -> None:
    provider = YahooChartProvider(
        FakeSession(
            FakeResponse(404),
            FakeResponse(429),
            FakeResponse(200, ValueError("bad")),
            requests.ConnectionError("down"),
            FakeResponse(200, {"chart": {"result": []}}),
            FakeResponse(200, CHART),
        )
    )
    day = date(2026, 11, 9)
    assert provider.history("X", day, day) is None
    for _ in range(3):
        with pytest.raises(ProviderError):
            provider.history("X", day, day)
    assert provider.history("X", day, day) is None
    assert provider.live_price("X") == 101.5
    assert provider.fundamentals("X") is None


class FakeTicker:
    def __init__(self, symbol: str, fail: bool = False) -> None:
        self.symbol, self.fail = symbol, fail
        self.history_metadata = {"currency": "USD"}
        self.fast_info = {"lastPrice": 12.5, "marketCap": 3e12}
        self.calendar = {"Earnings Date": [date(2026, 11, 12), "n/a"]}

    def history(self, **kwargs: Any) -> pd.DataFrame:
        if self.fail:
            raise RuntimeError("Too Many Requests")
        if self.symbol == "EMPTY":
            return pd.DataFrame()
        assert kwargs["auto_adjust"] is False
        index = pd.to_datetime(["2026-11-09", "2026-11-10"]).tz_localize("America/New_York")
        return pd.DataFrame(
            {
                "Open": [10.0, float("nan")],
                "Close": [11.0, 12.0],
                "Dividends": [0.0, 0.3],
                "Stock Splits": [4.0, 0.0],
            },
            index=index,
        )


class FakeYf:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def Ticker(self, symbol: str) -> FakeTicker:
        return FakeTicker(symbol, self.fail)


def test_yfinance_history_fundamentals_and_live() -> None:
    provider = YFinanceProvider(FakeYf())
    history = provider.history("AAPL", date(2026, 11, 9), date(2026, 11, 13))
    assert history is not None and history.currency == "USD"
    assert history.bars[date(2026, 11, 10)] == DailyBar(None, 12.0)
    assert history.dividends == [Dividend(date(2026, 11, 10), 0.3)]
    assert history.splits == [Split(date(2026, 11, 9), 4.0)]
    assert provider.history("EMPTY", date(2026, 11, 9), date(2026, 11, 13)) is None
    assert provider.live_price("AAPL") == 12.5
    assert provider.fundamentals("AAPL") == Fundamentals(3e12, (date(2026, 11, 12),))


def test_yfinance_errors_become_provider_errors() -> None:
    provider = YFinanceProvider(FakeYf(fail=True))
    with pytest.raises(ProviderError, match="Too Many Requests"):
        provider.history("AAPL", date(2026, 11, 9), date(2026, 11, 13))

    class Broken:
        def Ticker(self, symbol: str) -> Any:
            raise RuntimeError("boom")

    broken = YFinanceProvider(Broken())
    for call in (lambda: broken.live_price("A"), lambda: broken.fundamentals("A")):
        with pytest.raises(ProviderError):
            call()


def test_with_retries_backs_off_then_raises() -> None:
    sleeps: list[float] = []
    attempts = iter([ProviderError("1"), ProviderError("2"), "ok"])

    def flaky() -> str:
        value = next(attempts)
        if isinstance(value, Exception):
            raise value
        return value

    assert with_retries(flaky, (2, 4, 8), sleeps.append) == "ok"
    assert sleeps == [2, 4]

    def always() -> str:
        raise ProviderError("down")

    with pytest.raises(ProviderError, match="down"):
        with_retries(always, (1, 1), sleeps.append)


class Stub:
    def __init__(self, name: str, value: Any = None, error: bool = False) -> None:
        self.name, self.value, self.error, self.calls = name, value, error, 0

    def _answer(self, *args: Any) -> Any:
        self.calls += 1
        if self.error:
            raise ProviderError(self.name)
        return self.value

    history = live_price = fundamentals = _answer


def test_fallback_order_and_source() -> None:
    day = date(2026, 11, 9)
    history = History("X", "b")
    provider = FallbackProvider(
        Stub("a", error=True), Stub("b", history), delays=(1,), sleep=lambda _: None
    )
    assert provider.history("X", day, day) is history and provider.last_source == "b"
    assert provider.primary.calls == 2  # one retry before falling back
    primary_ok = FallbackProvider(Stub("a", 3.0), Stub("b", 4.0), delays=(), sleep=lambda _: None)
    assert primary_ok.live_price("X") == 3.0 and primary_ok.last_source == "a"
    nothing = FallbackProvider(
        Stub("a", None), Stub("b", error=True), delays=(), sleep=lambda _: None
    )
    assert nothing.fundamentals("X") is None and nothing.last_source is None


def test_default_provider() -> None:
    provider = default_provider()
    assert (provider.primary.name, provider.fallback.name) == ("yfinance", "yahoo-chart")
