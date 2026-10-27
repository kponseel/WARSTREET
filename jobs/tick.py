"""The single scheduled entry point (GitHub Actions `tick.yml`, every 15 minutes).

    python -m jobs.tick [--now 2026-11-13T21:45:00Z] [--no-live] [--log-format json]

Runs the due market transitions, then the due league transitions. Safe to run late, twice
or out of schedule: every transition is keyed and computed from "what should be true now".

Every tick is journaled in private.tick_runs (what ran, what waited, the log lines, the
error) and summarised in public.system_status (the app's status page). The process exits
with an error only when ticks fail ALERT_AFTER_FAILURES times in a row, so GitHub's
failure email means "look now", not "one provider hiccup".
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from datetime import UTC, datetime

from psycopg.types.json import Jsonb

from jobs.db import Connection, connect
from jobs.league_jobs import LeagueTickError, league_tick
from jobs.logs import TickCollector, redact, setup_logging
from jobs.market_jobs import market_tick
from jobs.prices import PriceProvider, default_provider

log = logging.getLogger("jobs.tick")

ALERT_AFTER_FAILURES = 2
TICK_LOG_RETENTION_DAYS = 30


class TickFailed(Exception):
    def __init__(self, done: list[str], error: str) -> None:
        super().__init__(error)
        self.done = done


def _run(
    conn: Connection,
    provider: PriceProvider,
    now: datetime,
    live: bool,
    league_ids: Sequence[str] | None,
) -> list[str]:
    market = market_tick(conn, provider, now, live=live)
    try:
        return market + league_tick(conn, now, league_ids)
    except LeagueTickError as error:
        raise TickFailed(market + error.done, str(error)) from error


def record_tick(
    conn: Connection,
    now: datetime,
    *,
    ok: bool,
    done: list[str],
    entries: list[dict[str, object]],
    error: str | None = None,
) -> int:
    """Journals one tick and updates the status row. Returns consecutive failures."""
    with conn.transaction():
        conn.execute(
            "insert into private.tick_runs (game_time, finished_at, ok, done, log, error) "
            "values (%s, now(), %s, %s, %s, %s)",
            (now, ok, Jsonb(done), Jsonb(entries), error),
        )
        conn.execute(
            "delete from private.tick_runs where started_at < now() - make_interval(days => %s)",
            (TICK_LOG_RETENTION_DAYS,),
        )
        row = conn.execute(
            "insert into public.system_status as s (id, last_tick_at, last_tick_ok, "
            "last_success_at, consecutive_failures, prices_updated_at, dev_clock, updated_at) "
            "values (true, now(), %(ok)s, case when %(ok)s then now() end, "
            "case when %(ok)s then 0 else 1 end, "
            "(select max(fetched_at) from public.reference_prices), "
            "exists (select 1 from private.dev_clock), now()) "
            "on conflict (id) do update set last_tick_at = excluded.last_tick_at, "
            "last_tick_ok = excluded.last_tick_ok, "
            "last_success_at = coalesce(excluded.last_success_at, s.last_success_at), "
            "consecutive_failures = case when excluded.last_tick_ok then 0 "
            "else s.consecutive_failures + 1 end, "
            "prices_updated_at = excluded.prices_updated_at, dev_clock = excluded.dev_clock, "
            "updated_at = excluded.updated_at "
            "returning consecutive_failures",
            {"ok": ok},
        ).fetchone()
    return int(row["consecutive_failures"]) if row else 0


def tick(
    conn: Connection,
    provider: PriceProvider,
    now: datetime,
    live: bool = True,
    league_ids: Sequence[str] | None = None,
) -> list[str]:
    """Runs one tick and journals it. Raises TickFailed when something failed."""
    with TickCollector() as collector:
        try:
            done = _run(conn, provider, now, live, league_ids)
        except TickFailed as failure:
            record_tick(
                conn,
                now,
                ok=False,
                done=failure.done,
                entries=collector.entries,
                error=str(failure),
            )
            raise
        except Exception as error:
            log.exception("tick failed")
            message = redact(f"{type(error).__name__}: {error}")
            record_tick(conn, now, ok=False, done=[], entries=collector.entries, error=message)
            raise TickFailed([], message) from error
    record_tick(conn, now, ok=True, done=done, entries=collector.entries)
    return done


def _instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the due game transitions")
    parser.add_argument("--now", type=_instant, default=None, help="fake clock (ISO, UTC)")
    parser.add_argument("--no-live", action="store_true", help="skip live price quotes")
    parser.add_argument("--log-format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    setup_logging(args.log_format)
    now = args.now or datetime.now(UTC)
    with connect() as conn:
        try:
            lines = tick(conn, default_provider(), now, live=not args.no_live)
        except TickFailed as failure:
            for line in failure.done:
                print(line)
            row = conn.execute(
                "select consecutive_failures from public.system_status where id"
            ).fetchone()
            failures = int(row["consecutive_failures"]) if row else 1
            log.error("tick failed (%s in a row): %s", failures, failure)
            return 1 if failures >= ALERT_AFTER_FAILURES else 0
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
