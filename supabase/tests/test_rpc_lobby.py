"""Lobby RPCs: create, join, leave, update, ready, start, locale (GAME_RULES §1)."""

from datetime import UTC, date, datetime

import pytest
from conftest import LOCK_AT, T_BEFORE_START, WEEK, Db, League, make_league

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
BASE = {
    "p_name": "League",
    "p_max_players": 4,
    "p_campaign_weeks": 8,
    "p_drone_enabled": True,
    "p_pseudo": "Alpha",
    "p_commander": "bastion",
    "p_avatar_color": "#1f3a5f",
}


def test_create_league_makes_host_a_member(db: Db) -> None:
    user = db.create_user()
    league_id = db.rpc(user, "create_league", **BASE)
    league = db.fetch_admin("select * from public.leagues where id = %s", (league_id,))[0]
    assert league["host_id"] == user and league["status"] == "lobby"
    assert len(league["invite_code"]) == 6 and set(league["invite_code"]) <= set(ALPHABET)
    members = db.fetch_admin(
        "select * from public.league_members where league_id = %s", (league_id,)
    )
    assert [(m["user_id"], m["pseudo"], m["ready"]) for m in members] == [(user, "Alpha", False)]


@pytest.mark.parametrize(
    ("override", "code"),
    [
        ({"p_name": "  "}, "LEAGUE_NAME_LENGTH"),
        ({"p_name": "x" * 41}, "LEAGUE_NAME_LENGTH"),
        ({"p_max_players": 2}, "MAX_PLAYERS_RANGE"),
        ({"p_max_players": 6}, "MAX_PLAYERS_RANGE"),
        ({"p_campaign_weeks": 3}, "CAMPAIGN_WEEKS_RANGE"),
        ({"p_campaign_weeks": 11}, "CAMPAIGN_WEEKS_RANGE"),
        ({"p_pseudo": "ab"}, "PSEUDO_LENGTH"),
        ({"p_pseudo": "x" * 17}, "PSEUDO_LENGTH"),
        ({"p_pseudo": "bad\x01name"}, "PSEUDO_INVALID"),
        ({"p_pseudo": "DRONE"}, "PSEUDO_RESERVED"),
        ({"p_commander": None}, "COMMANDER_REQUIRED"),
        ({"p_avatar_color": "#000000"}, "AVATAR_COLOR_INVALID"),
    ],
)
def test_create_league_rejections(db: Db, override: dict[str, object], code: str) -> None:
    user = db.create_user()
    assert db.rpc_error(user, "create_league", **{**BASE, **override}).code == code


def test_calls_without_a_session_are_rejected(db: Db) -> None:
    assert db.rpc_error(None, "create_league", **BASE).code == "NOT_AUTHENTICATED"


def _lobby(db: Db) -> tuple[str, object, object]:
    host = db.create_user()
    league_id = db.rpc(host, "create_league", **BASE)
    code = db.fetch_admin("select invite_code from public.leagues where id = %s", (league_id,))[0][
        "invite_code"
    ]
    return code, league_id, host


def test_join_league_accepts_a_code_in_any_case(db: Db) -> None:
    code, league_id, _ = _lobby(db)
    user = db.create_user()
    joined = db.rpc(
        user,
        "join_league",
        p_code=f"  {code.lower()} ",
        p_pseudo="Bravo",
        p_commander="shadow",
        p_avatar_color="#c2410c",
    )
    assert joined == league_id


def test_join_league_rejections(db: Db) -> None:
    code, _league_id, host = _lobby(db)
    user = db.create_user()
    args = {"p_pseudo": "Bravo", "p_commander": "shadow", "p_avatar_color": "#c2410c"}
    assert db.rpc_error(user, "join_league", p_code="ZZZZZZ", **args).code == "LEAGUE_NOT_FOUND"
    assert db.rpc_error(host, "join_league", p_code=code, **args).code == "ALREADY_MEMBER"
    taken = {**args, "p_pseudo": "alpha"}
    assert db.rpc_error(user, "join_league", p_code=code, **taken).code == "PSEUDO_TAKEN"
    for index in range(3):  # max_players = 4
        db.rpc(
            db.create_user(), "join_league", p_code=code, **{**args, "p_pseudo": f"Player{index}"}
        )
    error = db.rpc_error(user, "join_league", p_code=code, **args)
    assert (error.code, error.vars) == ("LEAGUE_FULL", {"max": 4})


def test_join_is_closed_after_start(db: Db) -> None:
    league = make_league(db)
    code = db.fetch_admin("select invite_code from public.leagues where id = %s", (league.id,))[0][
        "invite_code"
    ]
    error = db.rpc_error(
        league.outsider,
        "join_league",
        p_code=code,
        p_pseudo="Late",
        p_commander="bastion",
        p_avatar_color="#1f3a5f",
    )
    assert error.code == "LEAGUE_NOT_IN_LOBBY"


def test_leave_league(db: Db) -> None:
    code, league_id, host = _lobby(db)
    guest = db.create_user()
    db.rpc(
        guest,
        "join_league",
        p_code=code,
        p_pseudo="Bravo",
        p_commander="shadow",
        p_avatar_color="#c2410c",
    )
    assert db.rpc_error(db.create_user(), "leave_league", p_league=league_id).code == "NOT_A_MEMBER"

    db.rpc(host, "leave_league", p_league=league_id)  # host leaves: the guest becomes host
    league = db.fetch_admin("select host_id from public.leagues where id = %s", (league_id,))
    assert league == [{"host_id": guest}]

    db.rpc(guest, "leave_league", p_league=league_id)  # last member leaves: league deleted
    assert db.fetch_admin("select 1 from public.leagues where id = %s", (league_id,)) == []


def test_leave_is_closed_after_start(db: Db, league: League) -> None:
    assert db.rpc_error(league.users["B"], "leave_league", p_league=league.id).code == (
        "LEAGUE_NOT_IN_LOBBY"
    )


def test_update_member_and_ready(db: Db) -> None:
    code, league_id, _host = _lobby(db)
    guest = db.create_user()
    db.rpc(
        guest,
        "join_league",
        p_code=code,
        p_pseudo="Bravo",
        p_commander="shadow",
        p_avatar_color="#c2410c",
    )
    db.rpc(
        guest,
        "update_member",
        p_league=league_id,
        p_pseudo="Bravo",
        p_commander="berserker",
        p_avatar_color="#166534",
    )  # keeping one's own pseudo is fine
    error = db.rpc_error(
        guest,
        "update_member",
        p_league=league_id,
        p_pseudo="ALPHA",
        p_commander="berserker",
        p_avatar_color="#166534",
    )
    assert error.code == "PSEUDO_TAKEN"
    db.rpc(guest, "set_ready", p_league=league_id, p_ready=True)
    member = db.fetch_admin(
        "select commander, avatar_color, ready from public.league_members where user_id = %s",
        (guest,),
    )
    assert member == [{"commander": "berserker", "avatar_color": "#166534", "ready": True}]


def test_commanders_and_ready_are_locked_after_start(db: Db, league: League) -> None:
    user = league.users["B"]
    error = db.rpc_error(
        user,
        "update_member",
        p_league=league.id,
        p_pseudo="PBx",
        p_commander="shadow",
        p_avatar_color="#c2410c",
    )
    assert error.code == "LEAGUE_NOT_IN_LOBBY"
    assert db.rpc_error(user, "set_ready", p_league=league.id, p_ready=False).code == (
        "LEAGUE_NOT_IN_LOBBY"
    )


def test_start_campaign_rejections(db: Db) -> None:
    league = make_league(db, start=False)
    db.set_now(T_BEFORE_START)
    assert db.rpc_error(league.users["B"], "start_campaign", p_league=league.id).code == "NOT_HOST"
    db.rpc(league.users["C"], "set_ready", p_league=league.id, p_ready=False)
    error = db.rpc_error(league.host, "start_campaign", p_league=league.id)
    assert (error.code, error.vars) == ("NOT_ENOUGH_READY", {"ready": 2, "min": 3})


def test_start_campaign_creates_week_one_and_the_drone(db: Db) -> None:
    league = make_league(db, {"D": "technomancer"}, start=False)
    db.rpc(league.users["D"], "set_ready", p_league=league.id, p_ready=False)  # D plays anyway
    db.set_now(T_BEFORE_START)
    assert db.rpc(league.host, "start_campaign", p_league=league.id) == WEEK
    state = db.fetch_admin(
        "select status, start_week from public.leagues where id = %s", (league.id,)
    )
    assert state == [{"status": "active", "start_week": WEEK}]
    week = db.fetch_admin("select * from public.weeks where league_id = %s", (league.id,))[0]
    assert (week["number"], week["phase"], week["is_final"]) == (1, "briefing", False)
    assert week["lock_at"] == LOCK_AT
    assert week["resupply_closes_at"] == datetime(2026, 11, 12, 7, 59, 59, tzinfo=UTC)
    assert week["resupply_opens_at"] is None and week["debrief_at"] is None
    members = db.fetch_admin(
        "select pseudo, is_drone, commander from public.league_members where league_id = %s "
        "order by is_drone, pseudo",
        (league.id,),
    )
    assert len(members) == 5 and members[-1] == {
        "pseudo": "Drone",
        "is_drone": True,
        "commander": None,
    }
    assert db.rpc_error(league.host, "start_campaign", p_league=league.id).code == (
        "LEAGUE_NOT_IN_LOBBY"
    )


@pytest.mark.parametrize(
    ("now", "monday"),
    [
        (datetime(2026, 11, 8, 10, 59, 59, tzinfo=UTC), date(2026, 11, 9)),  # 13 h before lock
        (datetime(2026, 11, 8, 11, 0, 0, tzinfo=UTC), date(2026, 11, 16)),  # < 12 h before lock
        (datetime(2026, 11, 9, 8, 0, tzinfo=UTC), date(2026, 11, 16)),  # Monday morning
    ],
)
def test_late_start_moves_week_one(db: Db, now: datetime, monday: date) -> None:
    league = make_league(db, start=False)
    db.set_now(now)
    assert db.rpc(league.host, "start_campaign", p_league=league.id) == monday


def test_profile_is_created_and_locale_can_change(db: Db) -> None:
    user = db.create_user()
    assert db.select(user, "select locale from public.profiles") == [{"locale": "en"}]
    db.rpc(user, "set_locale", p_locale="fr")
    assert db.select(user, "select locale from public.profiles") == [{"locale": "fr"}]
    assert db.rpc_error(user, "set_locale", p_locale=None).code == "LOCALE_INVALID"
