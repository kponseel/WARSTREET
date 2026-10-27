"""Global market transitions (docs/ARCHITECTURE.md §6), keyed in `market_runs`.

Per exchange of the catalogue (`capture_p0:XPAR`, `capture_p_end:XNYS`…):
- capture_p0 / capture_p_mid: the session open, 10 min after it (live scores need them).
- capture_p_end: `debrief_delay_min` after the last close, the whole week is re-read in ONE
  fetch (one share basis) and P0, P_mid, P_end and dividends are rewritten together.
- confirm_p_end: one tick later, P_end is read again; a change is applied and logged.
- Provider down on Friday night: capture_p_end waits and retries for CAPTURE_GRACE, then
  takes the last live quote of the week as P_end, flagged `source = 'fallback:last_quote'`
  (the debrief shows it); a later read that works replaces it. With no quote at all the
  price stays missing and the unit scores 0 (flagged too, GAME_RULES §2).
Then `week_stats` prepares the next week (coef, Conflict Zone, weather…) once every exchange
is confirmed, and `live_prices` stores quotes while an exchange is open.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from engine import config
from engine.calendar import (
    MICS,
    SegmentSessions,
    segment_sessions,
    session_close,
    session_open,
    week_monday,
    week_sessions,
)
from engine.reference import instrument_week
from jobs.db import Connection, RetryLater, market_done, run_market_once
from jobs.market import CatalogueEntry, week_stats
from jobs.prices import PriceProvider

log = logging.getLogger(__name__)

CAPTURE_GRACE = timedelta(hours=2)  # after this, missing prices stay missing (flagged)
CONFIRM_DELAY = timedelta(minutes=15)  # second read of P_end, at least one tick later
FALLBACK_SOURCE = "fallback:last_quote"  # P_end taken from the last live quote of the week


@dataclass(frozen=True, slots=True)
class DbInstrument:
    id: int
    ticker: str
    region: str
    calendar_mic: str


def instruments(conn: Connection) -> list[DbInstrument]:
    rows = conn.execute(
        "select id, ticker, region::text as region, calendar_mic "
        "from public.instruments order by id"
    ).fetchall()
    return [DbInstrument(**row) for row in rows]


def _source(provider: PriceProvider) -> str:
    return getattr(provider, "last_source", None) or provider.name


def _upsert_price(
    conn: Connection,
    instrument_id: int,
    week: date,
    kind: str,
    price: float,
    dividend: float,
    source: str,
    confirmed: bool = False,
) -> None:
    conn.execute(
        "insert into public.reference_prices (instrument_id, week, kind, price, dividend, "
        "source, confirmed) values (%s, %s, %s, %s, %s, %s, %s) "
        "on conflict (instrument_id, week, kind) do update set price = excluded.price, "
        "dividend = excluded.dividend, source = excluded.source, fetched_at = now(), "
        "confirmed = excluded.confirmed",
        (instrument_id, week, kind, price, dividend, source, confirmed),
    )


def _capture_open(
    conn: Connection,
    provider: PriceProvider,
    insts: list[DbInstrument],
    monday: date,
    kind: str,
    session: date,
    deadline_passed: bool,
) -> None:
    missing = []
    for inst in insts:
        history = provider.history(inst.ticker, session, session)
        bar = history.bars.get(session) if history else None
        if bar is None or bar.open is None:
            missing.append(inst.ticker)
            continue
        _upsert_price(conn, inst.id, monday, kind, bar.open, 0.0, _source(provider))
    if missing and not deadline_passed:
        raise RetryLater(f"{kind} missing for {', '.join(missing[:5])}")
    if missing:
        log.warning("%s %s still missing after the grace period: %s", kind, monday, missing)


def _capture_week(
    conn: Connection,
    provider: PriceProvider,
    insts: list[DbInstrument],
    monday: date,
    sessions: SegmentSessions,
    deadline_passed: bool,
) -> None:
    """Rewrites P0, P_mid, P_end and dividends of the week from one fetch per instrument."""
    missing = []
    for inst in insts:
        history = provider.history(inst.ticker, monday, monday + timedelta(days=4))
        week = instrument_week(
            inst.id,
            inst.region,  # type: ignore[arg-type]
            sessions,
            history.bars if history else {},
            history.dividends if history else (),
        )
        source = _source(provider)
        for kind, price, dividend in (
            ("p0", week.p0, 0.0),
            ("p_mid", week.p_mid, week.d1),
            ("p_end", week.p_end, week.d2),
        ):
            if price is not None:
                _upsert_price(conn, inst.id, monday, kind, price, dividend, source)
        if week.p_end is None:
            missing.append(inst)
    if missing and not deadline_passed:
        raise RetryLater(f"p_end missing for {', '.join(i.ticker for i in missing[:5])}")
    if missing:
        _fallback_p_end(conn, missing, monday, sessions)


def _fallback_p_end(
    conn: Connection, insts: list[DbInstrument], monday: date, sessions: SegmentSessions
) -> None:
    """After the grace period: the last live quote of the week stands for P_end."""
    assert sessions.p_end is not None
    close = session_close(insts[0].calendar_mic, sessions.p_end)
    used, still_missing = [], []
    for inst in insts:
        quote = conn.execute(
            "select price from public.prices_live where instrument_id = %s "
            "and ts >= %s and ts <= %s order by ts desc limit 1",
            (inst.id, monday, close),
        ).fetchone()
        if quote is None:
            still_missing.append(inst.ticker)
            continue
        _upsert_price(conn, inst.id, monday, "p_end", float(quote["price"]), 0.0, FALLBACK_SOURCE)
        used.append(inst.ticker)
    if used:
        log.warning("p_end %s from the last live quote (provider down): %s", monday, used)
    if still_missing:
        log.warning("p_end %s still missing after the grace period: %s", monday, still_missing)


def _confirm_week(
    conn: Connection,
    provider: PriceProvider,
    insts: list[DbInstrument],
    monday: date,
    sessions: SegmentSessions,
) -> None:
    for inst in insts:
        row = conn.execute(
            "select price, source from public.reference_prices where instrument_id = %s "
            "and week = %s and kind = 'p_end'",
            (inst.id, monday),
        ).fetchone()
        if row is None:
            continue
        history = provider.history(inst.ticker, monday, monday + timedelta(days=4))
        week = instrument_week(
            inst.id,
            inst.region,  # type: ignore[arg-type]
            sessions,
            history.bars if history else {},
            history.dividends if history else (),
        )
        if week.p_end is not None and row["source"] == FALLBACK_SOURCE:
            log.warning("p_end of %s read again: the last quote is replaced", inst.ticker)
            conn.execute(
                "update public.reference_prices set price = %s, dividend = %s, source = %s, "
                "fetched_at = now() where instrument_id = %s and week = %s and kind = 'p_end'",
                (week.p_end, week.d2, _source(provider), inst.id, monday),
            )
        elif week.p_end is not None and abs(week.p_end - float(row["price"])) > 1e-9:
            log.warning(
                "p_end of %s changed on second read: %s -> %s",
                inst.ticker,
                row["price"],
                week.p_end,
            )
            conn.execute(
                "update public.reference_prices set price = %s, fetched_at = now() "
                "where instrument_id = %s and week = %s and kind = 'p_end'",
                (week.p_end, inst.id, monday),
            )
        conn.execute(
            "update public.reference_prices set confirmed = true where instrument_id = %s "
            "and week = %s and kind = 'p_end'",
            (inst.id, monday),
        )


def mics_with_sessions(monday: date) -> list[str]:
    return [mic for mic in MICS if segment_sessions(mic, monday).p_end is not None]


def week_confirmed(conn: Connection, monday: date) -> bool:
    """Every exchange that traded this week has its P_end confirmed."""
    return all(
        market_done(conn, monday, f"confirm_p_end:{mic}") for mic in mics_with_sessions(monday)
    )


def _write_week_stats(
    conn: Connection, provider: PriceProvider, insts: list[DbInstrument], week: date
) -> None:
    entries = [
        CatalogueEntry(i.ticker, i.ticker, i.region, i.calendar_mic, "", "")  # type: ignore[arg-type]
        for i in insts
    ]
    rows = week_stats(provider, entries, week)
    for inst, row in zip(insts, rows, strict=True):
        conn.execute(
            "insert into public.instrument_weeks (instrument_id, week, vol12w, coef, "
            "display_class, prev_week_return, max_abs_daily_move_prev, market_cap, "
            "earnings_date, in_conflict_zone, weather) "
            "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "on conflict (instrument_id, week) do update set vol12w = excluded.vol12w, "
            "coef = excluded.coef, display_class = excluded.display_class, "
            "prev_week_return = excluded.prev_week_return, "
            "max_abs_daily_move_prev = excluded.max_abs_daily_move_prev, "
            "market_cap = excluded.market_cap, earnings_date = excluded.earnings_date, "
            "in_conflict_zone = excluded.in_conflict_zone, weather = excluded.weather",
            (
                inst.id,
                week,
                row.vol12w,
                row.coef,
                row.display_class,
                row.prev_week_return,
                row.max_abs_daily_move_prev,
                row.market_cap,
                row.earnings_date,
                row.in_conflict_zone,
                row.weather,
            ),
        )


def _live_prices(
    conn: Connection, provider: PriceProvider, insts: Iterable[DbInstrument], now: datetime
) -> int:
    count = 0
    for inst in insts:
        price = provider.live_price(inst.ticker)
        if price is None:
            continue
        conn.execute(
            "insert into public.prices_live (instrument_id, ts, price) values (%s, %s, %s) "
            "on conflict do nothing",
            (inst.id, now, price),
        )
        count += 1
    conn.execute(
        "delete from public.prices_live where ts < %s",
        (now - timedelta(days=config.LIVE_PRICES_RETENTION_DAYS),),
    )
    return count


def write_sessions(conn: Connection, monday: date) -> int:
    """The week's trading sessions per exchange (display: the app's daily phase banner)."""
    exists = conn.execute(
        "select 1 from public.market_sessions where session between %s and %s limit 1",
        (monday, monday + timedelta(days=4)),
    ).fetchone()
    if exists:
        return 0
    count = 0
    with conn.transaction():
        for mic in MICS:
            for session in week_sessions(mic, monday):
                conn.execute(
                    "insert into public.market_sessions (mic, session, open_at, close_at) "
                    "values (%s, %s, %s, %s) on conflict do nothing",
                    (mic, session, session_open(mic, session), session_close(mic, session)),
                )
                count += 1
    return count


def open_mics(now: datetime) -> list[str]:
    """Exchanges in session at `now` (from the calendars, never hardcoded hours)."""
    monday = week_monday(now)
    return [
        mic
        for mic in MICS
        if any(
            session_open(mic, s) <= now < session_close(mic, s) for s in week_sessions(mic, monday)
        )
    ]


def market_tick(
    conn: Connection, provider: PriceProvider, now: datetime, live: bool = True
) -> list[str]:
    """Runs every due market transition; returns the transitions done in this tick."""
    done: list[str] = []
    monday = week_monday(now)
    insts = instruments(conn)
    for week in (monday, monday + timedelta(days=7)):
        if write_sessions(conn, week):
            done.append(f"sessions {week}")
    delay = timedelta(minutes=config.PRICE_CAPTURE_DELAY_MIN)
    end_delay = timedelta(minutes=config.DEBRIEF_DELAY_MIN)
    for mic in MICS:
        group = [i for i in insts if i.calendar_mic == mic]
        if not group:
            continue
        sessions = segment_sessions(mic, monday)
        for kind, session in (("p0", sessions.p0), ("p_mid", sessions.p_mid)):
            if session is None:
                continue
            opened = session_open(mic, session)
            if now >= opened + delay:
                name = f"capture_{kind}:{mic}"
                if run_market_once(
                    conn,
                    monday,
                    name,
                    lambda k=kind, s=session, o=opened, g=group: _capture_open(
                        conn, provider, g, monday, k, s, now >= o + CAPTURE_GRACE
                    ),
                ):
                    done.append(name)
        if sessions.p_end is None:
            continue
        closed = session_close(mic, sessions.p_end) + end_delay
        if now >= closed:
            name = f"capture_p_end:{mic}"
            if run_market_once(
                conn,
                monday,
                name,
                lambda s=sessions, c=closed, g=group: _capture_week(
                    conn, provider, g, monday, s, now >= c + CAPTURE_GRACE
                ),
            ):
                done.append(name)
        captured_earlier = f"capture_p_end:{mic}" not in done and market_done(
            conn, monday, f"capture_p_end:{mic}"
        )  # the second read is always a later tick, even when a tick runs late
        if now >= closed + CONFIRM_DELAY and captured_earlier:
            name = f"confirm_p_end:{mic}"
            if run_market_once(
                conn,
                monday,
                name,
                lambda s=sessions, g=group: _confirm_week(conn, provider, g, monday, s),
            ):
                done.append(name)
    next_week = monday + timedelta(days=7)
    if week_confirmed(conn, monday) and run_market_once(
        conn, next_week, "week_stats", lambda: _write_week_stats(conn, provider, insts, next_week)
    ):
        done.append(f"week_stats {next_week}")
    mics = set(open_mics(now)) if live else set()
    if mics:
        with conn.transaction():
            count = _live_prices(conn, provider, [i for i in insts if i.calendar_mic in mics], now)
        done.append(f"live_prices {count}")
    return done


def bootstrap_week_stats(conn: Connection, provider: PriceProvider, week: date) -> bool:
    """Stats for a week when none exist yet (first deployment, replay)."""
    exists = conn.execute(
        "select 1 from public.instrument_weeks where week = %s limit 1", (week,)
    ).fetchone()
    if exists:
        return False
    insts = instruments(conn)
    return run_market_once(
        conn, week, "week_stats", lambda: _write_week_stats(conn, provider, insts, week)
    )


def reference_prices(conn: Connection, week: date) -> dict[int, dict[str, Any]]:
    """{instrument_id: {kind: price, 'd1': .., 'd2': ..}} for a week."""
    result: dict[int, dict[str, Any]] = {}
    for row in conn.execute(
        "select instrument_id, kind::text as kind, price, dividend from public.reference_prices "
        "where week = %s",
        (week,),
    ).fetchall():
        entry = result.setdefault(row["instrument_id"], {"d1": 0.0, "d2": 0.0})
        entry[row["kind"]] = float(row["price"])
        if row["kind"] == "p_mid":
            entry["d1"] = float(row["dividend"])
        elif row["kind"] == "p_end":
            entry["d2"] = float(row["dividend"])
    return result
