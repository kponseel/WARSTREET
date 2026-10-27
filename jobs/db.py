"""Database access for the jobs: a direct Postgres connection (psycopg).

The connection string comes from the SUPABASE_DB_URL environment variable (a GitHub
Actions secret). It is never printed or logged. Every transition runs in ONE transaction
together with its idempotence key, so a doubled or late cron run never applies twice.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

import psycopg
from psycopg.rows import dict_row

ENV_VAR = "SUPABASE_DB_URL"
log = logging.getLogger(__name__)

Connection = psycopg.Connection[dict[str, Any]]


class RetryLater(Exception):
    """Raised inside a transition when its data is not ready yet: the transaction (and its
    idempotence key) is rolled back and the next tick tries again."""


def connect(url: str | None = None) -> Connection:
    url = url or os.environ.get(ENV_VAR)
    if not url:
        raise SystemExit(f"{ENV_VAR} is not set")
    # prepare_threshold=None: Supabase's transaction pooler does not support prepared
    # statements.
    return psycopg.connect(
        url,
        row_factory=dict_row,
        autocommit=True,  # each `with conn.transaction()` is then a real transaction
        application_name="warstreet-jobs",
        prepare_threshold=None,
    )


def _run(
    conn: Connection, insert: str, params: tuple[Any, ...], label: str, work: Callable[[], None]
) -> bool:
    try:
        with conn.transaction():
            if conn.execute(insert, params).fetchone() is None:
                return False  # already done
            work()
    except RetryLater as reason:
        log.info("%s: not ready (%s)", label, reason)
        return False
    log.info("%s: done", label)
    return True


def run_market_once(conn: Connection, week: Any, transition: str, work: Callable[[], None]) -> bool:
    return _run(
        conn,
        "insert into public.market_runs (week, transition) values (%s, %s) "
        "on conflict do nothing returning week",
        (week, transition),
        f"market {week} {transition}",
        work,
    )


def run_league_once(
    conn: Connection, league_id: Any, week: Any, transition: str, work: Callable[[], None]
) -> bool:
    return _run(
        conn,
        "insert into public.job_runs (league_id, week, transition) values (%s, %s, %s) "
        "on conflict do nothing returning week",
        (league_id, week, transition),
        f"league {str(league_id)[:8]} {week} {transition}",
        work,
    )


def market_done(conn: Connection, week: Any, transition: str) -> bool:
    row = conn.execute(
        "select 1 from public.market_runs where week = %s and transition = %s",
        (week, transition),
    ).fetchone()
    return row is not None
