"""RPC rate limit (migration 16): the PostgREST pre-request hook, called as the API does."""

from __future__ import annotations

import uuid

import psycopg
from conftest import Db, League
from psycopg import errors


def hook(db: Db, user: uuid.UUID | None, path: str = "/rpc/set_locale") -> str:
    """One API request's pre-request call: 'ok' or the refusal code."""
    db.as_user(user)
    db.conn.execute("select set_config('request.path', %s, true)", (path,))
    try:
        with db.conn.transaction():
            db.conn.execute("select private.check_request()")
    except errors.RaiseException as exc:
        return exc.diag.message_primary or ""
    finally:
        db.admin()
    return "ok"


def limit(db: Db) -> int:
    rows = db.fetch_admin(
        "select value from public.game_config where key = 'rpc_rate_limit_per_minute'"
    )
    return int(rows[0]["value"])


def calls(db: Db, user: uuid.UUID) -> list[int]:
    rows = db.fetch_admin("select calls from private.rpc_calls where user_id = %s", (user,))
    return [row["calls"] for row in rows]


def test_rpc_calls_are_limited_per_user_and_minute(db: Db, league: League) -> None:
    a, b = league.users["A"], league.users["B"]
    n = limit(db)
    assert [hook(db, a) for _ in range(n)] == ["ok"] * n
    assert hook(db, a) == "RATE_LIMITED"
    assert hook(db, a) == "RATE_LIMITED"  # still refused: the crossing call rolled back
    assert calls(db, a) == [n]
    assert hook(db, b) == "ok"  # per user


def test_only_rpc_calls_of_a_user_are_counted(db: Db, league: League) -> None:
    a = league.users["A"]
    assert hook(db, a, "/leagues") == "ok"
    assert hook(db, None) == "ok"  # no user (anon): nothing to count
    assert calls(db, a) == []
    assert hook(db, a) == "ok"
    assert calls(db, a) == [1]


def test_older_minutes_are_dropped(db: Db, league: League) -> None:
    a = league.users["A"]
    db.exec_admin(
        "insert into private.rpc_calls (user_id, minute, calls) "
        "values (%s, date_trunc('minute', now()) - interval '5 minutes', 999)",
        (a,),
    )
    assert hook(db, a) == "ok"
    assert calls(db, a) == [1]


def test_read_only_requests_are_not_counted(database_url: str) -> None:
    # Stable RPCs (server_time, order_costs) run read-only: the hook must not write.
    with psycopg.connect(database_url) as conn:
        conn.execute("begin read only")
        conn.execute("set local role authenticated")
        conn.execute("select set_config('request.jwt.claim.sub', %s, true)", (str(uuid.uuid4()),))
        conn.execute("select set_config('request.path', '/rpc/server_time', true)")
        conn.execute("select private.check_request()")
        conn.rollback()
