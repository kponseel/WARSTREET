"""Simulation toolkit shared by `jobs.replay` and `jobs.dev` (never used by the cron).

- Price providers for a simulated clock: `HistoricalProvider` wraps any provider (real
  Yahoo bars, or `SyntheticMarket` for weeks that have not happened yet), fetches each
  ticker once and gives live quotes as of the simulated time. `DiskCache` keeps fetched
  histories under `.cache/prices/` so repeated simulations do not hit Yahoo again.
- `as_user`: calls a player RPC exactly like the app (role `authenticated` + JWT claims).
- `week_instants`: every instant at which something happens in a week, for stepping a
  fake clock through it.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any

from psycopg.types.json import Jsonb

from engine import config
from engine.calendar import (
    MICS,
    local_instant,
    phase_timestamps,
    segment_sessions,
    session_close,
    session_open,
    week_sessions,
)
from engine.reference import DailyBar, Dividend
from jobs.db import Connection
from jobs.league_jobs import THURSDAY_DISPATCH_LOCAL_TIME
from jobs.market_jobs import CONFIRM_DELAY
from jobs.prices import Fundamentals, History, PriceProvider, Split

CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache" / "prices"
LIVE_HOURS_UTC = range(6, 23)  # hourly ticks during the week, so live scores move


def parse_week(value: str) -> date:
    """`2026-W43` (ISO week) or any date of the week -> its Monday."""
    if "W" in value:
        year, week = value.split("-W")
        return date.fromisocalendar(int(year), int(week), 1)
    day = date.fromisoformat(value)
    return day - timedelta(days=day.weekday())


def last_complete_week(today: date) -> date:
    """The Monday of the last week whose Friday close is behind us."""
    monday = today - timedelta(days=today.weekday())
    return monday - timedelta(days=7) if today.weekday() < 5 else monday


# --- price providers ------------------------------------------------------------------------
class SyntheticMarket:
    """Deterministic random walks for any date (future weeks, offline runs). Each ticker
    has its own volatility, so coefficients and display classes vary like real stocks."""

    name = "synthetic"
    last_source = "synthetic"
    ORIGIN = date(2020, 1, 1)

    @staticmethod
    @cache
    def _path(ticker: str) -> dict[date, DailyBar]:
        rng = random.Random(f"synthetic:{ticker}")
        vol = rng.uniform(0.008, 0.035)
        price, bars, day = rng.uniform(20, 400), {}, SyntheticMarket.ORIGIN
        end = date(2031, 1, 1)
        while day < end:
            if day.weekday() < 5:
                opened = price * math.exp(rng.gauss(0, vol / 3))
                price = opened * math.exp(rng.gauss(0.0002, vol))
                bars[day] = DailyBar(round(opened, 4), round(price, 4))
            day += timedelta(days=1)
        return bars

    def history(self, ticker: str, start: date, end: date) -> History | None:
        history = History(ticker, self.name, None)
        history.bars = {d: b for d, b in self._path(ticker).items() if start <= d <= end}
        return history

    def live_price(self, ticker: str) -> float | None:  # pragma: no cover - via the wrapper
        return None

    def fundamentals(self, ticker: str) -> Fundamentals | None:
        rng = random.Random(f"fundamentals:{ticker}")
        return Fundamentals(rng.uniform(1e9, 3e12), ())


@dataclass
class DiskCache:
    """Caches `history()` results on disk (JSON, one file per ticker and range)."""

    base: PriceProvider
    directory: Path = CACHE_DIR

    @property
    def name(self) -> str:
        return self.base.name

    @property
    def last_source(self) -> str:
        return getattr(self.base, "last_source", None) or self.base.name

    def _file(self, ticker: str, start: date, end: date) -> Path:
        safe = ticker.replace("/", "_")
        return self.directory / f"{safe}_{start.isoformat()}_{end.isoformat()}.json"

    def history(self, ticker: str, start: date, end: date) -> History | None:
        path = self._file(ticker, start, end)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if data is None:
                return None
            history = History(ticker, data["source"], data["currency"])
            history.bars = {date.fromisoformat(d): DailyBar(*b) for d, b in data["bars"].items()}
            history.dividends = [Dividend(date.fromisoformat(d), a) for d, a in data["dividends"]]
            history.splits = [Split(date.fromisoformat(d), r) for d, r in data["splits"]]
            return history
        history = self.base.history(ticker, start, end)
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = None
        if history is not None:
            payload = {
                "source": history.source,
                "currency": history.currency,
                "bars": {d.isoformat(): [b.open, b.close] for d, b in history.bars.items()},
                "dividends": [[x.ex_date.isoformat(), x.amount] for x in history.dividends],
                "splits": [[x.day.isoformat(), x.ratio] for x in history.splits],
            }
        path.write_text(json.dumps(payload), encoding="utf-8")
        return history

    def live_price(self, ticker: str) -> float | None:
        return self.base.live_price(ticker)

    def fundamentals(self, ticker: str) -> Fundamentals | None:
        path = self.directory / f"{ticker.replace('/', '_')}_fundamentals.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if data is None:
                return None
            return Fundamentals(
                data["market_cap"], tuple(date.fromisoformat(d) for d in data["earnings"])
            )
        result = self.base.fundamentals(ticker)
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = (
            None
            if result is None
            else {
                "market_cap": result.market_cap,
                "earnings": [d.isoformat() for d in result.earnings_dates],
            }
        )
        path.write_text(json.dumps(payload), encoding="utf-8")
        return result


@dataclass
class HistoricalProvider:
    """Daily bars fetched once per ticker over [start, end], never beyond the simulated
    clock; a live quote is a straight line from the session open to its close."""

    base: PriceProvider
    start: date
    end: date
    mics: dict[str, str] = field(default_factory=dict)
    now: datetime = field(default_factory=lambda: datetime.now(UTC))
    name: str = "replay"
    _cache: dict[str, History | None] = field(default_factory=dict)

    @property
    def last_source(self) -> str:
        return f"replay:{getattr(self.base, 'last_source', None) or self.base.name}"

    def _full(self, ticker: str) -> History | None:
        if ticker not in self._cache:
            self._cache[ticker] = self.base.history(ticker, self.start, self.end)
        return self._cache[ticker]

    def history(self, ticker: str, start: date, end: date) -> History | None:
        full = self._full(ticker)
        if full is None:
            return None
        part = History(ticker, full.source, full.currency, splits=list(full.splits))
        part.bars = {d: b for d, b in full.bars.items() if start <= d <= end}
        part.dividends = [x for x in full.dividends if start <= x.ex_date <= end]
        return part

    def live_price(self, ticker: str) -> float | None:
        full, mic = self._full(ticker), self.mics.get(ticker)
        if full is None or mic is None:
            return None
        for day in sorted(full.bars, reverse=True):
            bar = full.bars[day]
            opened, closed = session_open(mic, day), session_close(mic, day)
            if opened > self.now:
                continue
            if self.now >= closed or bar.open is None or bar.close is None:
                return bar.close
            elapsed = (self.now - opened) / (closed - opened)
            return bar.open + (bar.close - bar.open) * elapsed
        return None

    def fundamentals(self, ticker: str) -> Fundamentals | None:
        return self.base.fundamentals(ticker)


# --- acting as a player --------------------------------------------------------------------
def set_fake_now(conn: Connection, now: datetime | None) -> None:
    """This session's clock (app.fake_now; '' = back to the dev clock or the real time)."""
    conn.execute("select set_config('app.fake_now', %s, false)", (now.isoformat() if now else "",))


def as_user(conn: Connection, user_id: str, function: str, **params: Any) -> Any:
    """Calls an RPC the way the app does (role `authenticated` + the user's JWT claims)."""
    args = ", ".join(f"{name} => %({name})s" for name in params)
    values = {k: Jsonb(v) if isinstance(v, dict | list) else v for k, v in params.items()}
    claims = json.dumps({"sub": user_id, "role": "authenticated"})
    with conn.transaction():
        conn.execute("select set_config('request.jwt.claims', %s, true)", (claims,))
        conn.execute("select set_config('request.jwt.claim.sub', %s, true)", (user_id,))
        conn.execute("set local role authenticated")
        row = conn.execute(f"select public.{function}({args}) as result", values).fetchone()
        # Back to the admin identity (a savepoint release would keep the local settings).
        conn.execute("reset role")
        conn.execute("select set_config('request.jwt.claims', '', true)")
        conn.execute("select set_config('request.jwt.claim.sub', '', true)")
    return row["result"] if row else None


# --- the week's instants --------------------------------------------------------------------
def briefing_opens(monday: date) -> datetime:
    """When bots draft: the Saturday before the week, noon Paris."""
    return local_instant(monday - timedelta(days=2), "12:00:00")


def week_instants(monday: date, live_hours: bool = True) -> list[datetime]:
    """Every instant at which a transition of the week becomes due (plus hourly ticks)."""
    ts = phase_timestamps(monday)
    instants = {
        briefing_opens(monday),
        ts.lock_at + timedelta(seconds=1),
        ts.resupply_opens_at + timedelta(minutes=1),
        ts.resupply_closes_at + timedelta(seconds=1),
        local_instant(monday + timedelta(days=3), THURSDAY_DISPATCH_LOCAL_TIME),
    }
    delay = timedelta(minutes=config.PRICE_CAPTURE_DELAY_MIN)
    end_delay = timedelta(minutes=config.DEBRIEF_DELAY_MIN)
    for mic in MICS:
        sessions = segment_sessions(mic, monday)
        for session in (sessions.p0, sessions.p_mid):
            if session is not None:
                instants.add(session_open(mic, session) + delay)
        if sessions.p_end is not None:
            closed = session_close(mic, sessions.p_end) + end_delay
            instants |= {closed, closed + CONFIRM_DELAY, closed + 2 * CONFIRM_DELAY}
    if live_hours:
        for day in week_sessions("XNYS", monday):
            for hour in LIVE_HOURS_UTC:
                instants.add(datetime(day.year, day.month, day.day, hour, 30, tzinfo=UTC))
    end = ts.debrief_at + 3 * CONFIRM_DELAY
    return sorted(i for i in instants if i <= end)
