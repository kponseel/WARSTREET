"""Dev mode (jobs.dev): a league of bots plays a whole week on synthetic prices."""

from datetime import date

import pytest
from conftest import Db

from jobs import dev
from jobs.bots import league_bots

MONDAY = date(2026, 11, 9)


@pytest.fixture
def league(db: Db) -> str:
    db.admin()
    result = dev.create_league(
        db.conn, monday=MONDAY, bot_count=4, me=[], weeks=4, start=True, prices="synthetic"
    )
    return str(result["league_id"])


def count(db: Db, query: str, params: object) -> int:
    return len(db.fetch_admin(query, params))


def test_bots_draft_then_the_week_plays_out(db: Db, league: str) -> None:
    assert len(league_bots(db.conn, league)) == 4
    dev.advance(
        db.conn, league, dev.target_instant(db.conn, league, "briefing"), prices="synthetic"
    )
    assert (
        count(db, "select 1 from public.squads where league_id = %s and not auto", (league,)) == 4
    )
    assert db.fetch_admin("select private.clock() as c")[0]["c"] == dev.now_of(db.conn)

    dev.advance(db.conn, league, dev.target_instant(db.conn, league, "debrief"), prices="synthetic")
    finals = db.fetch_admin(
        "select rank from public.scores_final where league_id = %s and week = %s", (league, MONDAY)
    )
    assert len(finals) == 5  # 4 bots + the Drone
    assert (
        count(
            db, "select 1 from public.events where league_id = %s and kind = 'dispatch'", (league,)
        )
        == 3
    )
    state = dev.inspect(db.conn, league)
    assert state["dev_clock"] and len(state["members"]) == 5
    assert any(run.endswith("debrief") for run in state["job_runs"])
    assert all(t["ok"] for t in dev.tick_logs(db.conn, 50, errors_only=False))


def test_the_clock_cannot_go_back(db: Db, league: str) -> None:
    with pytest.raises(SystemExit):
        dev.advance(db.conn, league, dev.now_of(db.conn), prices="synthetic")


def test_dev_refuses_a_remote_database() -> None:
    with pytest.raises(SystemExit, match="local database"):
        dev.main(["--db", "postgresql://u:p@db.example.com:5432/postgres", "logs"])
