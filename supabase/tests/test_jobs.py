"""Jobs against the database: a whole week tick by tick, idempotence, masking."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from conftest import OTHER_SQUAD, T_BRIEFING, WEEK, Db, League, make_league
from fake_market import FakeMarket

from jobs.tick import TickFailed, tick

MONDAY_EU = datetime(2026, 11, 9, 8, 15, tzinfo=UTC)
WEDNESDAY_NIGHT = datetime(2026, 11, 11, 22, 0, tzinfo=UTC)
THURSDAY = datetime(2026, 11, 12, 9, 15, tzinfo=UTC)
FRIDAY_CAPTURE = datetime(2026, 11, 13, 21, 35, tzinfo=UTC)
FRIDAY_CONFIRM = datetime(2026, 11, 13, 21, 50, tzinfo=UTC)
NEXT_WEEK = date(2026, 11, 16)


def run(db: Db, market: FakeMarket, now: datetime) -> list[str]:
    db.admin()
    return tick(db.conn, market, now)


def keyed(lines: list[str]) -> list[str]:
    return [line for line in lines if "live_" not in line]


@pytest.fixture
def week(db: Db) -> League:
    league = make_league(db, {"A": "bastion", "B": "hunter", "C": "shadow"})
    league.save_squad("A")
    league.save_squad("B", OTHER_SQUAD)
    # The fixture's Conflict Zone stands for this week's stats (no recompute from FakeMarket).
    db.exec_admin(
        "insert into public.market_runs (week, transition) values (%s, 'week_stats')", (WEEK,)
    )
    db.set_now(T_BRIEFING)
    league.give_ammo("A", 5)
    db.rpc(league.users["A"], "play_order", p_league=league.id, p_type="force_field")
    return league


def count(db: Db, query: str, params: object = None) -> int:
    return len(db.fetch_admin(query, params))


def test_a_whole_week(db: Db, week: League) -> None:
    market = FakeMarket(earnings={"AAPL": date(2026, 11, 17)})
    lid = week.id

    # Saturday: briefing opens, ammo income (3 each, week 1; A is near the cap of 5).
    lines = run(db, market, T_BRIEFING)
    assert any("open_briefing" in line for line in lines)
    # The previous week's P_end is confirmed on a later tick, then nothing is left to do.
    assert all(line.startswith("confirm_p_end:") for line in keyed(run(db, market, T_BRIEFING)))
    assert keyed(run(db, market, T_BRIEFING)) == []
    balances = db.fetch_admin(
        "select member_id, sum(delta)::int as b from public.ammo_ledger "
        "where league_id = %s and reason = 'income' group by member_id",
        (lid,),
    )
    by_member = {r["member_id"]: r["b"] for r in balances}
    assert by_member[week.members["A"]] == 5 - 4  # 5 given - force field 1, capped at 5
    assert by_member[week.members["B"]] == 3 and by_member[week.members["C"]] == 3
    weeks = db.fetch_admin("select * from public.weeks where league_id = %s", (lid,))
    assert weeks[0]["resupply_opens_at"] == datetime(2026, 11, 11, 21, 5, tzinfo=UTC)
    assert weeks[0]["debrief_at"] == datetime(2026, 11, 13, 21, 30, tzinfo=UTC)

    # Monday: lock (C and the Drone get squads), EU P0 captured, first Dispatch.
    db.set_now(MONDAY_EU)
    lines = run(db, market, MONDAY_EU)
    assert any(line.endswith(" lock") for line in lines)
    assert "capture_p0:XPAR" in lines and "capture_p0:XNYS" not in lines
    assert any("dispatch_monday" in line for line in lines)
    squads = db.fetch_admin(
        "select member_id, auto, locked from public.squads where league_id = %s", (lid,)
    )
    assert len(squads) == 4 and all(s["locked"] for s in squads)
    assert {s["member_id"] for s in squads if s["auto"]} == {
        week.members["C"],
        week.members["Drone"],
    }
    assert keyed(run(db, market, MONDAY_EU)) == []

    # Live table: no Shadow row, the Drone without rank.
    public = db.fetch_admin(
        "select member_id, pf_live, rank_live from public.scores_live_public where league_id = %s",
        (lid,),
    )
    members = {r["member_id"]: r for r in public}
    assert week.members["C"] not in members
    assert members[week.members["Drone"]]["rank_live"] is None
    assert sorted(r["rank_live"] for m, r in members.items() if m != week.members["Drone"]) == [
        1,
        2,
    ]

    # Wednesday night and Thursday: resupply, swaps, Thursday Dispatch.
    run(db, market, WEDNESDAY_NIGHT)
    assert (
        db.fetch_admin("select phase::text from public.weeks where league_id = %s", (lid,))[0][
            "phase"
        ]
        == "resupply"
    )
    db.set_now(WEDNESDAY_NIGHT)
    db.rpc(
        week.users["A"], "swap_unit", p_league=lid, p_slot="marksman", p_reserve_slot="reserve_2"
    )
    lines = run(db, market, THURSDAY)
    assert any("close_resupply" in line for line in lines)
    assert any("dispatch_thursday" in line for line in lines)
    units = db.fetch_admin(
        "select slot::text, active_s2 from public.squad_units where member_id = %s",
        (week.members["A"],),
    )
    assert {u["slot"]: u["active_s2"] for u in units}["reserve_2"] is True

    # Friday: captured, then confirmed one tick later, then the debrief.
    lines = run(db, market, FRIDAY_CAPTURE)
    assert "capture_p_end:XNYS" in lines and not any("debrief" in line for line in lines)
    lines = run(db, market, FRIDAY_CONFIRM)
    assert "confirm_p_end:XNYS" in lines and f"week_stats {NEXT_WEEK}" in lines
    assert any(line.endswith(" debrief") for line in lines)
    # Next tick: the next week's briefing opens (ammo income), then nothing is left.
    assert [line.split()[-1] for line in keyed(run(db, market, FRIDAY_CONFIRM))] == [
        "open_briefing"
    ]
    assert keyed(run(db, market, FRIDAY_CONFIRM)) == []

    final = db.fetch_admin(
        "select member_id, rank, campaign_points, pf_total from "
        "public.scores_final where league_id = %s",
        (lid,),
    )
    assert len(final) == 4
    humans = [r for r in final if r["member_id"] != week.members["Drone"]]
    assert sorted(float(r["campaign_points"]) for r in humans) in (
        [2, 5, 10],
        [3.5, 3.5, 10],
        [2, 7.5, 7.5],
        [17 / 3] * 3,
    )
    pg = db.fetch_admin(
        "select r.dividend from public.reference_prices r join public.instruments i "
        "on i.id = r.instrument_id where i.ticker = 'PG' and r.kind = 'p_end' "
        "and r.week = %s",
        (WEEK,),
    )
    assert pg == [{"dividend": 1}]  # Friday ex-date: S2
    assert (
        count(db, "select 1 from public.events where league_id = %s and kind = 'dispatch'", (lid,))
        == 3
    )
    assert (
        count(
            db,
            "select 1 from public.instrument_weeks where week = %s and in_conflict_zone",
            (NEXT_WEEK,),
        )
        == 8
    )
    nxt = db.fetch_admin(
        "select number, phase::text from public.weeks where league_id = %s and week = %s",
        (lid, NEXT_WEEK),
    )
    assert nxt == [{"number": 2, "phase": "briefing"}]


def test_jammed_player_is_masked_and_never_leads_the_dispatch(db: Db, week: League) -> None:
    market = FakeMarket()
    week.give_ammo("B", 5)
    db.set_now(T_BRIEFING + timedelta(minutes=1))  # after A's force field
    db.rpc(
        week.users["B"],
        "play_order",
        p_league=week.id,
        p_type="jamming",
        p_target_member=week.members["A"],
    )  # blocked by A's earlier force field
    db.rpc(
        week.users["B"],
        "play_order",
        p_league=week.id,
        p_type="jamming",
        p_target_member=week.members["A"],
    )  # this one lands
    run(db, market, T_BRIEFING)
    run(db, market, MONDAY_EU)
    row = db.fetch_admin(
        "select pf_live, rank_live, jammed, units from public.scores_live_public "
        "where member_id = %s",
        (week.members["A"],),
    )[0]
    assert row == {"pf_live": None, "rank_live": None, "jammed": True, "units": {}}
    statuses = sorted(
        r["status"]
        for r in db.fetch_admin(
            "select status::text from public.orders where member_id = %s", (week.members["B"],)
        )
    )
    assert statuses == ["applied", "blocked"]
    pseudo_a = db.fetch_admin(
        "select pseudo from public.league_members where member_id = %s", (week.members["A"],)
    )[0]["pseudo"]
    monday = db.fetch_admin("select template_key, vars from public.events where kind = 'dispatch'")
    assert monday and monday[0]["vars"].get("leader") != pseudo_a
    # The private live score of a jammed player is hidden from them too (RLS).
    assert db.select(week.users["A"], "select 1 from public.scores_live") == []


def test_lock_waits_for_the_conflict_zone(db: Db) -> None:
    league = make_league(db)
    db.exec_admin(
        "update public.instrument_weeks set in_conflict_zone = false where week = %s", (WEEK,)
    )
    run(db, FakeMarket(), T_BRIEFING)
    lines = run(db, FakeMarket(), MONDAY_EU)
    assert not any(line.endswith(" lock") for line in lines)
    assert count(db, "select 1 from public.squads where league_id = %s", (league.id,)) == 0
    # Nothing that follows the lock happens without it, the debrief included.
    for now in (WEDNESDAY_NIGHT, THURSDAY, FRIDAY_CAPTURE, FRIDAY_CONFIRM):
        assert [line for line in run(db, FakeMarket(), now) if str(league.id)[:8] in line] == []
    assert count(db, "select 1 from public.scores_final where league_id = %s", (league.id,)) == 0


def test_a_failing_league_does_not_block_the_others(
    db: Db, monkeypatch: pytest.MonkeyPatch
) -> None:
    import jobs.league_jobs as league_jobs

    broken, healthy = make_league(db), make_league(db)
    real = league_jobs._open_briefing

    def open_briefing(conn: object, data: league_jobs.WeekData) -> None:
        if data.league_id == str(broken.id):
            raise RuntimeError("boom")
        real(conn, data)  # type: ignore[arg-type]

    monkeypatch.setattr(league_jobs, "_open_briefing", open_briefing)
    db.exec_admin("delete from public.system_status")  # a clean status row for this test
    with pytest.raises(TickFailed) as info:
        run(db, FakeMarket(), T_BRIEFING)
    cause = info.value.__cause__
    assert isinstance(cause, league_jobs.LeagueTickError)
    assert cause.failed == [str(broken.id)[:8]]
    assert f"{str(healthy.id)[:8]} {WEEK} open_briefing" in info.value.done
    assert count(db, "select 1 from public.job_runs where league_id = %s", (broken.id,)) == 0
    # Journaled: the failed tick, its error and the log lines of the failing transition.
    last = db.fetch_admin("select ok, error, log from private.tick_runs order by id desc limit 1")[
        0
    ]
    assert last["ok"] is False and str(broken.id)[:8] in last["error"]
    assert any(
        e.get("transition") == "open_briefing" and e["level"] == "error" for e in last["log"]
    )
    status = db.fetch_admin("select last_tick_ok, consecutive_failures from public.system_status")
    assert status == [{"last_tick_ok": False, "consecutive_failures": 1}]
    with pytest.raises(TickFailed):
        run(db, FakeMarket(), T_BRIEFING)
    assert db.fetch_admin("select consecutive_failures from public.system_status") == [
        {"consecutive_failures": 2}
    ]
    monkeypatch.setattr(league_jobs, "_open_briefing", real)
    run(db, FakeMarket(), T_BRIEFING)
    assert db.fetch_admin(
        "select last_tick_ok, consecutive_failures from public.system_status"
    ) == [{"last_tick_ok": True, "consecutive_failures": 0}]


def test_replay_of_a_demo_week(db: Db) -> None:
    from jobs.replay import parse_week, replay

    db.admin()
    assert parse_week("2026-W46") == WEEK == parse_week("2026-11-12")
    result = replay(db.conn, FakeMarket(), WEEK, "demo")
    assert len(result["scores"]) == 5  # 4 bots and the Drone
    # Four ranked bots (ties share a rank: 1, 2, 3, 3 is valid), the Drone unranked.
    ranks = sorted(r["rank"] for r in result["scores"] if r["rank"])
    assert len(ranks) == 4 and ranks[0] == 1
    assert all(rank == index + 1 or rank == ranks[index - 1] for index, rank in enumerate(ranks))
    keys = [d["template_key"] for d in result["dispatches"]]
    assert keys[1:] == ["dispatch.thursday", "dispatch.debrief"]
    assert all(d["en"] and d["fr"] and "{" not in d["en"] + d["fr"] for d in result["dispatches"])
    assert any(line.endswith(" debrief") for line in result["transitions"])


def test_monday_dispatch_ignores_implausible_moves(db: Db, week: League) -> None:
    """A split over the weekend (Friday close no longer comparable) is never headlined."""
    market = FakeMarket()
    run(db, market, T_BRIEFING)
    run(db, market, T_BRIEFING)
    db.exec_admin(
        "update public.reference_prices set price = price / 100 where week = %s and kind = 'p_end'",
        (date(2026, 11, 2),),
    )
    run(db, market, MONDAY_EU)
    monday = db.fetch_admin(
        "select vars from public.events where league_id = %s and kind = 'dispatch'", (week.id,)
    )
    assert monday[0]["vars"]["mover"] == "-"


def test_sessions_and_live_returns_for_the_front(db: Db, week: League) -> None:
    market = FakeMarket()
    run(db, market, T_BRIEFING)
    sessions = db.fetch_admin(
        "select mic, count(*)::int as n from public.market_sessions "
        "where session between %s and %s group by mic",
        (WEEK, date(2026, 11, 13)),
    )
    assert {r["mic"]: r["n"] for r in sessions}["XNYS"] == 5  # 9-13 Nov, no US holiday
    run(db, market, MONDAY_EU)
    user = week.users["A"]
    returns = db.select(
        user,
        "select r.week_return_pct, r.last_price from public.live_returns r "
        "join public.instruments i on i.id = r.instrument_id where i.ticker = 'MC.PA' "
        "and r.week = %s",
        (WEEK,),
    )
    assert len(returns) == 1 and returns[0]["last_price"] is not None
    assert db.select(None, "select 1 from public.market_sessions limit 1") != []
