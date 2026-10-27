"""Price providers (docs/ARCHITECTURE.md §6).

Two providers behind one `PriceProvider` protocol:
- `YFinanceProvider`: `yfinance` with `auto_adjust=False` (prices adjusted for splits, never
  for dividends; the engine adds dividends back itself).
- `YahooChartProvider`: the Yahoo chart HTTP API called directly. Used as the fallback when
  yfinance is rate-limited (it often is on GitHub runners). It has no market cap and no
  earnings dates: those come back as missing, never invented.

`FallbackProvider` retries the primary with backoff, then falls back per ticker, and
records which source answered. Missing data is reported as None or an empty history.
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol

import requests

from engine.reference import DailyBar, Dividend

log = logging.getLogger(__name__)

CHART_URL = "https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
USER_AGENT = "Mozilla/5.0 (compatible; warstreet-prices/1.0)"
RETRY_DELAYS = (2.0, 4.0, 8.0)


@dataclass(frozen=True, slots=True)
class Split:
    day: date
    ratio: float  # new shares per old share


@dataclass(slots=True)
class History:
    """Daily data of one ticker from one fetch (one share basis)."""

    ticker: str
    source: str
    currency: str | None = None
    bars: dict[date, DailyBar] = field(default_factory=dict)
    dividends: list[Dividend] = field(default_factory=list)
    splits: list[Split] = field(default_factory=list)

    @property
    def closes(self) -> dict[date, float]:
        return {d: b.close for d, b in self.bars.items() if b.close is not None}


@dataclass(frozen=True, slots=True)
class Fundamentals:
    market_cap: float | None
    earnings_dates: tuple[date, ...]


class PriceProvider(Protocol):
    name: str

    def history(self, ticker: str, start: date, end: date) -> History | None:
        """Daily bars, dividends and splits for sessions in [start, end]; None if unknown."""
        ...

    def live_price(self, ticker: str) -> float | None: ...

    def fundamentals(self, ticker: str) -> Fundamentals | None: ...


class ProviderError(Exception):
    """A provider call failed (network, rate limit, unexpected payload)."""


def _number(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    return None if math.isnan(number) else number


def with_retries[T](
    call: Callable[[], T],
    delays: Iterable[float] = RETRY_DELAYS,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Calls `call`, retrying on ProviderError after each delay; re-raises the last error."""
    last: ProviderError | None = None
    for delay in (0.0, *delays):
        if delay:
            sleep(delay)
        try:
            return call()
        except ProviderError as error:
            last = error
            log.warning("price provider error: %s", error)
    assert last is not None
    raise last


# --- yfinance ----------------------------------------------------------------------------
class YFinanceProvider:
    name = "yfinance"

    def __init__(self, module: Any = None) -> None:
        if module is None:
            import yfinance as module  # heavy import, only when used
        self._yf = module

    def history(self, ticker: str, start: date, end: date) -> History | None:
        try:
            handle = self._yf.Ticker(ticker)
            frame = handle.history(
                start=start.isoformat(),
                end=(end + timedelta(days=1)).isoformat(),
                auto_adjust=False,
                actions=True,
            )
            metadata = handle.history_metadata or {}
        except Exception as error:  # yfinance raises many types, incl. rate limits
            raise ProviderError(f"yfinance {ticker}: {type(error).__name__}: {error}") from error
        if frame is None or len(frame) == 0:
            return None
        result = History(ticker=ticker, source=self.name, currency=metadata.get("currency"))
        for stamp, row in frame.iterrows():
            day = stamp.date()
            result.bars[day] = DailyBar(
                open=_number(row.get("Open")), close=_number(row.get("Close"))
            )
            dividend = _number(row.get("Dividends"))
            if dividend:
                result.dividends.append(Dividend(day, dividend))
            split = _number(row.get("Stock Splits"))
            if split:
                result.splits.append(Split(day, split))
        return result

    def live_price(self, ticker: str) -> float | None:
        try:
            return _number(self._yf.Ticker(ticker).fast_info.get("lastPrice"))
        except Exception as error:
            raise ProviderError(f"yfinance live {ticker}: {error}") from error

    def fundamentals(self, ticker: str) -> Fundamentals | None:
        try:
            handle = self._yf.Ticker(ticker)
            market_cap = _number(handle.fast_info.get("marketCap"))
            calendar = handle.calendar or {}
        except Exception as error:
            raise ProviderError(f"yfinance fundamentals {ticker}: {error}") from error
        raw = calendar.get("Earnings Date", []) if isinstance(calendar, Mapping) else []
        dates = tuple(d for d in raw if isinstance(d, date))
        return Fundamentals(market_cap=market_cap, earnings_dates=dates)


# --- Yahoo chart API (fallback) -------------------------------------------------------------
class YahooChartProvider:
    name = "yahoo-chart"

    def __init__(self, session: Any = None, timeout: float = 20.0) -> None:
        self._session = session or requests.Session()
        self._timeout = timeout

    def _chart(self, ticker: str, params: Mapping[str, Any]) -> dict[str, Any] | None:
        try:
            response = self._session.get(
                CHART_URL.format(ticker=ticker),
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=self._timeout,
            )
        except requests.RequestException as error:
            raise ProviderError(f"chart {ticker}: {error}") from error
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise ProviderError(f"chart {ticker}: HTTP {response.status_code}")
        try:
            results = response.json()["chart"]["result"]
        except (ValueError, KeyError, TypeError) as error:
            raise ProviderError(f"chart {ticker}: unexpected payload") from error
        return results[0] if results else None

    def history(self, ticker: str, start: date, end: date) -> History | None:
        period1 = int(datetime.combine(start, datetime.min.time(), UTC).timestamp())
        period2 = int(
            datetime.combine(end + timedelta(days=1), datetime.min.time(), UTC).timestamp()
        )
        chart = self._chart(
            ticker,
            {"period1": period1, "period2": period2, "interval": "1d", "events": "div,splits"},
        )
        if chart is None or not chart.get("timestamp"):
            return None
        meta = chart.get("meta", {})
        offset = timedelta(seconds=int(meta.get("gmtoffset", 0)))
        quote = chart["indicators"]["quote"][0]
        result = History(ticker=ticker, source=self.name, currency=meta.get("currency"))
        for index, stamp in enumerate(chart["timestamp"]):
            day = (datetime.fromtimestamp(stamp, UTC) + offset).date()
            if start <= day <= end:
                result.bars[day] = DailyBar(
                    open=_number(quote["open"][index]), close=_number(quote["close"][index])
                )
        events = chart.get("events", {})
        for item in events.get("dividends", {}).values():
            day = (datetime.fromtimestamp(item["date"], UTC) + offset).date()
            if start <= day <= end:
                result.dividends.append(Dividend(day, float(item["amount"])))
        for item in events.get("splits", {}).values():
            day = (datetime.fromtimestamp(item["date"], UTC) + offset).date()
            if start <= day <= end:
                ratio = float(item["numerator"]) / float(item["denominator"])
                result.splits.append(Split(day, ratio))
        result.dividends.sort(key=lambda d: d.ex_date)
        return result

    def live_price(self, ticker: str) -> float | None:
        chart = self._chart(ticker, {"range": "1d", "interval": "1d"})
        return _number(chart.get("meta", {}).get("regularMarketPrice")) if chart else None

    def fundamentals(self, ticker: str) -> Fundamentals | None:
        return None  # not available from the chart API: reported as missing


# --- fallback --------------------------------------------------------------------------------
class FallbackProvider:
    """Primary with retries, then the fallback, per ticker. `last_source` tells which one
    answered the last call (stored in reference_prices.source)."""

    name = "fallback"

    def __init__(
        self,
        primary: PriceProvider,
        fallback: PriceProvider,
        delays: Iterable[float] = RETRY_DELAYS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.primary, self.fallback = primary, fallback
        self._delays, self._sleep = tuple(delays), sleep
        self.last_source: str | None = None

    def _call(self, method: str, *args: Any) -> Any:
        for provider in (self.primary, self.fallback):
            try:
                value = with_retries(
                    lambda p=provider: getattr(p, method)(*args), self._delays, self._sleep
                )
            except ProviderError:
                continue
            if value is not None:
                self.last_source = provider.name
                return value
        self.last_source = None
        return None

    def history(self, ticker: str, start: date, end: date) -> History | None:
        return self._call("history", ticker, start, end)  # type: ignore[no-any-return]

    def live_price(self, ticker: str) -> float | None:
        return self._call("live_price", ticker)  # type: ignore[no-any-return]

    def fundamentals(self, ticker: str) -> Fundamentals | None:
        return self._call("fundamentals", ticker)  # type: ignore[no-any-return]


def default_provider() -> FallbackProvider:
    return FallbackProvider(YFinanceProvider(), YahooChartProvider())
