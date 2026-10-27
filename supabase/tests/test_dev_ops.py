"""Dev clock, server_time() and the operations tables (migration 12)."""

from datetime import UTC, datetime

import psycopg
import pytest
from conftest import T_BRIEFING, Db

DEV_NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)


def test_without_dev_clock_server_time_is_the_real_time(db: Db) -> None:
    user = db.create_user()
    before = db.fetch_admin("select now() as n")[0]["n"]
    served = db.select(user, "select public.server_time() as t")[0]["t"]
    assert abs((served - before).total_seconds()) < 5


def test_dev_clock_applies_to_api_sessions_too(db: Db) -> None:
    user = db.create_user()
    db.exec_admin("insert into private.dev_clock (fake_now) values (%s)", (DEV_NOW,))
    assert db.select(user, "select public.server_time() as t") == [{"t": DEV_NOW}]
    assert db.fetch_admin("select private.clock() as c") == [{"c": DEV_NOW}]
    # A direct session's fake clock (tests, replay) still wins.
    db.set_now(T_BRIEFING)
    assert db.fetch_admin("select private.clock() as c") == [{"c": T_BRIEFING}]


def test_running_dev_clock_moves_forward(db: Db) -> None:
    db.exec_admin(
        "insert into private.dev_clock (fake_now, running, set_at) "
        "values (%s, true, now() - interval '90 seconds')",
        (DEV_NOW,),
    )
    clock = db.fetch_admin("select private.clock() as c")[0]["c"]
    assert 89 <= (clock - DEV_NOW).total_seconds() <= 95


def test_system_status_is_read_only_for_players(db: Db) -> None:
    db.exec_admin(
        "insert into public.system_status (last_tick_ok) values (true) "
        "on conflict (id) do update set last_tick_ok = true"
    )
    user = db.create_user()
    assert db.select(user, "select last_tick_ok from public.system_status") == [
        {"last_tick_ok": True}
    ]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.select(user, "update public.system_status set last_tick_ok = false returning 1")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.select(user, "select * from private.tick_runs")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.select(user, "select * from private.dev_clock")
