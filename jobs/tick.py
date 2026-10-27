"""The single scheduled entry point (GitHub Actions `tick.yml`, every 15 minutes).

    python -m jobs.tick [--now 2026-11-13T21:45:00Z] [--no-live]

Runs the due market transitions, then the due league transitions. Safe to run late, twice
or out of schedule: every transition is keyed and computed from "what should be true now".
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from datetime import UTC, datetime

from jobs.db import Connection, connect
from jobs.league_jobs import league_tick
from jobs.market_jobs import market_tick
from jobs.prices import PriceProvider, default_provider


def tick(
    conn: Connection,
    provider: PriceProvider,
    now: datetime,
    live: bool = True,
    league_ids: Sequence[str] | None = None,
) -> list[str]:
    return market_tick(conn, provider, now, live=live) + league_tick(conn, now, league_ids)


def _instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the due game transitions")
    parser.add_argument("--now", type=_instant, default=None, help="fake clock (ISO, UTC)")
    parser.add_argument("--no-live", action="store_true", help="skip live price quotes")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    now = args.now or datetime.now(UTC)
    with connect() as conn:
        for line in tick(conn, default_provider(), now, live=not args.no_live):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
