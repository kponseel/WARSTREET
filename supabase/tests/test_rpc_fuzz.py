"""RPC fuzzing (milestone 09): no identity, the wrong league, garbage parameters, wrong phase.

Every refusal must be a clean error code from private.raise_error (which the app
translates), never an internal error, and a refused call must leave the tables as they
were. Every player RPC is listed in RPCS; a test fails if a new one is not.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import psycopg
import pytest
from conftest import (
    LOCK_AT,
    RESUPPLY_CLOSES_AT,
    T_AFTER_LOCK,
    T_BEFORE_START,
    T_BRIEFING,
    T_DEBRIEF,
    T_RESUPPLY,
    T_S2,
    VALID_SQUAD,
    Db,
    League,
    RpcError,
    make_league,
)
from psycopg.types.json import Jsonb
from test_static import _error_codes

KNOWN_CODES = set(_error_codes())

# Game tables a player action can change (row fingerprints compared before and after).
TABLES = (
    "leagues",
    "league_members",
    "squads",
    "squad_units",
    "swaps",
    "orders",
    "pacts",
    "ammo_ledger",
    "events",
    "profiles",
)


def outcome(db: Db, user: uuid.UUID | None, function: str, **params: Any) -> str:
    """'ok', the refusal code, or 'INTERNAL <sqlstate>' for anything that is not clean."""
    try:
        db.rpc(user, function, **params)
    except RpcError as exc:
        return exc.code
    except psycopg.Error as exc:  # the call ran in a savepoint: the test goes on
        return f"INTERNAL {exc.sqlstate}"
    return "ok"


def fingerprint(db: Db) -> dict[str, str]:
    result = {}
    for table in TABLES:
        row = db.fetch_admin(
            f"select coalesce(md5(string_agg(t::text, '|' order by t::text)), '') as h "
            f"from public.{table} t"
        )
        result[table] = row[0]["h"]
    return result


def calls(league: League, partner: uuid.UUID, pact: uuid.UUID) -> dict[str, dict[str, Any]]:
    """One well-formed call per player RPC, for `league`."""
    return {
        "create_league": {
            "p_name": "Fuzz",
            "p_max_players": 4,
            "p_campaign_weeks": 8,
            "p_drone_enabled": True,
            "p_pseudo": "Fuzzer",
            "p_commander": "hunter",
            "p_avatar_color": "#1f3a5f",
        },
        "join_league": {
            "p_code": "ABCDEFGH",
            "p_pseudo": "Fuzzer",
            "p_commander": "hunter",
            "p_avatar_color": "#1f3a5f",
        },
        "league_preview": {"p_code": "ABCDEFGH"},
        "leave_league": {"p_league": league.id},
        "update_member": {
            "p_league": league.id,
            "p_pseudo": "Fuzzer",
            "p_commander": "hunter",
            "p_avatar_color": "#1f3a5f",
        },
        "set_ready": {"p_league": league.id, "p_ready": True},
        "start_campaign": {"p_league": league.id},
        "save_squad": {"p_league": league.id, "p_units": league.squad_ids(VALID_SQUAD)},
        "swap_unit": {"p_league": league.id, "p_slot": "marksman", "p_reserve_slot": "reserve_2"},
        "cancel_swap": {"p_league": league.id, "p_slot": "marksman"},
        "play_order": {
            "p_league": league.id,
            "p_type": "jamming",
            "p_target_member": partner,
            "p_target_slot": None,
        },
        "order_costs": {"p_league": league.id},
        "propose_pact": {"p_league": league.id, "p_partner": partner},
        "accept_pact": {"p_pact": pact},
        "decline_pact": {"p_pact": pact},
        "set_locale": {"p_locale": "fr"},
        "server_time": {},
    }


RPCS = (
    "accept_pact",
    "cancel_swap",
    "create_league",
    "decline_pact",
    "join_league",
    "league_preview",
    "leave_league",
    "order_costs",
    "play_order",
    "propose_pact",
    "save_squad",
    "server_time",
    "set_locale",
    "set_ready",
    "start_campaign",
    "swap_unit",
    "update_member",
)


def test_every_player_rpc_is_fuzzed(db: Db) -> None:
    rows = db.fetch_admin(
        "select p.proname from pg_proc p join pg_namespace n on n.oid = p.pronamespace "
        "where n.nspname = 'public' and has_function_privilege('authenticated', p.oid, 'execute')"
    )
    assert {r["proname"] for r in rows} == set(RPCS)


def _pact(db: Db, league: League) -> uuid.UUID:
    league.db.set_now(T_BRIEFING)
    db.rpc(league.users["A"], "propose_pact", p_league=league.id, p_partner=league.members["B"])
    return db.fetch_admin("select id from public.pacts where league_id = %s", (league.id,))[0]["id"]


def test_no_identity_is_refused_everywhere(db: Db, league: League) -> None:
    pact = _pact(db, league)
    before = fingerprint(db)
    for function, params in calls(league, league.members["B"], pact).items():
        result = outcome(db, None, function, **params)
        if function == "server_time":  # the clock is not a secret
            assert result == "ok"
        else:
            assert result == "NOT_AUTHENTICATED", function
    assert fingerprint(db) == before


def test_an_outsider_cannot_act_on_a_league(db: Db, league: League) -> None:
    pact = _pact(db, league)
    league.save_squad("A")
    before = fingerprint(db)
    league_rpcs = {"create_league", "join_league", "league_preview", "set_locale", "server_time"}
    for when in (T_BRIEFING, T_RESUPPLY):
        league.open_resupply()
        db.set_now(when)
        for function, params in calls(league, league.members["B"], pact).items():
            if function in league_rpcs:
                continue
            result = outcome(db, league.outsider, function, **params)
            assert result in {"NOT_A_MEMBER", "PACT_NOT_FOUND"}, (function, result)
    assert fingerprint(db) == before


def test_targets_from_another_league_are_refused(db: Db, league: League) -> None:
    other = make_league(db, {"A": "hunter", "B": "bastion"})
    league.save_squad("A")
    league.give_ammo("A", 10)
    pact = _pact(db, other)  # a pact between two players of the other league
    db.set_now(T_BRIEFING)
    before = fingerprint(db)
    stranger = other.members["B"]
    for order in ("jamming", "blockade", "intel"):
        result = outcome(
            db,
            league.users["A"],
            "play_order",
            p_league=league.id,
            p_type=order,
            p_target_member=stranger,
            p_target_slot=None,
        )
        assert result == "INVALID_TARGET", order
    assert (
        outcome(db, league.users["A"], "propose_pact", p_league=league.id, p_partner=stranger)
        == "INVALID_TARGET"
    )
    for function in ("accept_pact", "decline_pact"):  # A is not part of that pact
        assert outcome(db, league.users["A"], function, p_pact=pact) in {
            "NOT_A_MEMBER",
            "PACT_NOT_FOUND",
            "NOT_PACT_PARTNER",
        }
    # The other league's id with this league's member ids: still not a member there.
    assert (
        outcome(
            db,
            league.users["C"],
            "save_squad",
            p_league=other.id,
            p_units=league.squad_ids(VALID_SQUAD),
        )
        == "NOT_A_MEMBER"
    )
    assert fingerprint(db) == before


TEXTS = ("", " ", "x" * 10_000, "'; drop table public.leagues; --", "<script>", "‮", "😀" * 50)
UUIDS = (None, uuid.UUID(int=0), uuid.uuid4())
INTS = (None, -1, 0, 2**31 - 1, -(2**31))


def _squad_garbage(league: League) -> list[Any]:
    valid = league.squad_ids(VALID_SQUAD)
    return [
        None,
        [],
        "squad",
        1,
        True,
        {},
        {"champion": 1.5},
        {**valid, "champion": 1.0},
        {**valid, "champion": 1e12},
        {**valid, "champion": -1},
        {**valid, "champion": 0},
        {**valid, "champion": None},
        {**valid, "champion": "1"},
        {**valid, "champion": [valid["champion"]]},
        {**valid, "champion": {"id": valid["champion"]}},
        {**valid, "x" * 1000: valid["champion"]},
        {**valid, "reserve_3": 7},
        {**valid, "reserve_1": valid["champion"]},
    ]


def _variants(params: dict[str, Any], garbage: Callable[[str], list[Any]]) -> list[dict[str, Any]]:
    """The call with one parameter at a time replaced by each of its garbage values."""
    out = []
    for name in params:
        for value in garbage(name):
            out.append({**params, name: value})
    return out


def test_garbage_parameters_give_clean_codes(db: Db, league: League) -> None:
    pact = _pact(db, league)
    league.give_ammo("A", 10)

    def garbage(name: str) -> list[Any]:
        if name in {"p_league", "p_pact", "p_partner", "p_target_member"}:
            return list(UUIDS)
        if name in {"p_name", "p_pseudo", "p_avatar_color", "p_code"}:
            return [None, *TEXTS]
        if name in {"p_max_players", "p_campaign_weeks"}:
            return list(INTS)
        if name in {"p_ready", "p_drone_enabled"}:
            return [None]
        if name == "p_units":  # PostgREST passes any JSON value as jsonb
            return [None if v is None else Jsonb(v) for v in _squad_garbage(league)]
        return [None]  # enums: a wrong label never reaches the function (cast error)

    internal: list[tuple[str, str, Any, str]] = []
    for when in (T_BEFORE_START, T_BRIEFING, T_RESUPPLY):
        league.open_resupply()
        db.set_now(when)
        for function, params in calls(league, league.members["B"], pact).items():
            for variant in _variants(params, garbage):
                result = outcome(db, league.users["A"], function, **variant)
                if result != "ok" and result not in KNOWN_CODES:
                    changed = next(k for k in variant if variant[k] is not params[k])
                    value = variant[changed]
                    shown = repr(value.obj if isinstance(value, Jsonb) else value)[:40]
                    internal.append((function, changed, shown, result))
    assert internal == [], "\n".join(map(str, sorted(set(internal))))


@pytest.mark.parametrize(
    ("when", "allowed"),
    [
        (T_BRIEFING, {"save_squad", "play_order:briefing", "propose_pact"}),
        (T_AFTER_LOCK, set()),
        (T_RESUPPLY, {"swap_unit", "play_order:resupply"}),  # pacts: briefing only (§7)
        (RESUPPLY_CLOSES_AT.replace(second=59, minute=59), set()),
        (T_S2, set()),
        (T_DEBRIEF, set()),
    ],
)
def test_actions_only_in_their_window(db: Db, league: League, when: Any, allowed: set[str]) -> None:
    league.save_squad("A")
    league.give_ammo("A", 10)
    league.open_resupply()
    if when > LOCK_AT:
        db.exec_admin("update public.squads set locked = true where league_id = %s", (league.id,))
    db.set_now(when)
    target = league.members["B"]
    actions: dict[str, tuple[str, dict[str, Any]]] = {
        "save_squad": (
            "save_squad",
            {"p_league": league.id, "p_units": league.squad_ids(VALID_SQUAD)},
        ),
        "play_order:briefing": (
            "play_order",
            {"p_league": league.id, "p_type": "blockade", "p_target_member": target},
        ),
        "play_order:resupply": (
            "play_order",
            {"p_league": league.id, "p_type": "pillage", "p_target_member": target},
        ),
        "swap_unit": (
            "swap_unit",
            {"p_league": league.id, "p_slot": "marksman", "p_reserve_slot": "reserve_2"},
        ),
        "propose_pact": ("propose_pact", {"p_league": league.id, "p_partner": target}),
    }
    window_codes = {
        "BRIEFING_CLOSED",
        "RESUPPLY_CLOSED",
        "ORDER_WINDOW_CLOSED",
        "ORDER_WRONG_WINDOW",
        "LEAGUE_NOT_ACTIVE",
    }
    for name, (function, params) in actions.items():
        db.conn.execute("savepoint action")
        result = outcome(db, league.users["A"], function, **params)
        db.conn.execute("rollback to savepoint action")
        if name in allowed:
            assert result == "ok", (name, result)
        else:
            assert result in window_codes, (name, result)
