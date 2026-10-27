"""Squad RPCs: save_squad during briefing, swaps during resupply (GAME_RULES §3)."""

import pytest
from conftest import (
    OTHER_SQUAD,
    RESUPPLY_CLOSES_AT,
    RESUPPLY_OPENS_AT,
    T_AFTER_LOCK,
    T_BRIEFING,
    T_RESUPPLY,
    VALID_SQUAD,
    WEEK,
    Db,
    League,
    make_league,
)


def _save(league: League, who: str, squad: dict[str, str]) -> str:
    league.db.set_now(T_BRIEFING)
    return league.db.rpc_error(
        league.users[who], "save_squad", p_league=league.id, p_units=league.squad_ids(squad)
    ).code


def test_save_squad_stores_front_and_reserve(db: Db, league: League) -> None:
    league.save_squad("A")
    league.save_squad("A", OTHER_SQUAD)  # saving again replaces the draft
    units = db.fetch_admin(
        "select u.slot::text, i.ticker, u.active_s1, u.active_s2 from public.squad_units u "
        "join public.instruments i on i.id = u.instrument_id where u.member_id = %s order by 1",
        (league.members["A"],),
    )
    assert {u["slot"]: u["ticker"] for u in units} == OTHER_SQUAD
    assert all(
        u["active_s1"] == u["active_s2"] == (not u["slot"].startswith("reserve")) for u in units
    )
    squad = db.fetch_admin(
        "select auto, locked, submitted_at from public.squads where member_id = %s",
        (league.members["A"],),
    )[0]
    assert squad["submitted_at"] == T_BRIEFING and not squad["auto"] and not squad["locked"]


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"general": "KO"}, "SQUAD_UNKNOWN_SLOT"),
        ({"reserve_3": "KO"}, "SQUAD_UNKNOWN_SLOT"),  # only the Quartermaster has 3 reserves
        ({"champion": None}, "SQUAD_MISSING_SLOT"),
        ({"reserve_2": None}, "SQUAD_MISSING_SLOT"),
        ({"reserve_2": "AAPL"}, "SQUAD_DUPLICATE_INSTRUMENT"),
        ({"veteran": "KO", "saboteur": "PEP"}, "FRONT_NEEDS_REGION"),  # 0 EU
        ({"veteran": "KO", "marksman": "MC.PA"}, "VETERAN_SAME_REGION"),  # both US
        (
            {
                "champion": "MC.PA",
                "veteran": "AAPL",
                "saboteur": "SAP.DE",
                "marksman": "AIR.PA",
                "priority_target": "JPM",
                "reserve_1": "TTE.PA",
                "reserve_2": "PEP",
            },
            "PRIORITY_TARGET_NOT_IN_ZONE",
        ),
        ({"reserve_1": "PEP"}, "RESERVE_NEEDS_REGION"),  # 2 US in reserve
    ],
)
def test_save_squad_rule_rejections(
    league: League, change: dict[str, str | None], code: str
) -> None:
    squad = {k: v for k, v in {**VALID_SQUAD, **change}.items() if v is not None}
    assert _save(league, "A", squad) == code


def test_save_squad_malformed_payloads(db: Db, league: League) -> None:
    db.set_now(T_BRIEFING)
    user = league.users["A"]
    assert (
        db.rpc_error(user, "save_squad", p_league=league.id, p_units=[1, 2]).code == "SQUAD_INVALID"
    )
    units = {**league.squad_ids(VALID_SQUAD), "champion": 999999}
    assert (
        db.rpc_error(user, "save_squad", p_league=league.id, p_units=units).code
        == "UNKNOWN_INSTRUMENT"
    )
    units = {**league.squad_ids(VALID_SQUAD), "champion": "AAPL"}
    assert (
        db.rpc_error(user, "save_squad", p_league=league.id, p_units=units).code
        == "UNKNOWN_INSTRUMENT"
    )


def test_region_error_carries_variables(league: League) -> None:
    league.db.set_now(T_BRIEFING)
    squad = {**VALID_SQUAD, "veteran": "KO", "saboteur": "PEP"}
    error = league.db.rpc_error(
        league.users["A"], "save_squad", p_league=league.id, p_units=league.squad_ids(squad)
    )
    assert error.vars == {"region": "EU", "min": 2, "count": 0}


def test_conflict_zone_must_exist(db: Db, league: League) -> None:
    db.exec_admin(
        "update public.instrument_weeks set in_conflict_zone = false where week = %s", (WEEK,)
    )
    assert _save(league, "A", VALID_SQUAD) == "CONFLICT_ZONE_NOT_READY"


def test_quartermaster_needs_three_reserves(db: Db) -> None:
    league = make_league(db, {"A": "quartermaster"})
    assert _save(league, "A", VALID_SQUAD) == "SQUAD_MISSING_SLOT"
    league.save_squad("A", {**VALID_SQUAD, "reserve_3": "KO"})


def test_save_squad_after_lock_is_rejected_even_if_phase_is_stale(db: Db, league: League) -> None:
    db.set_now(T_AFTER_LOCK)  # weeks.phase is still 'briefing': the clock decides
    error = db.rpc_error(
        league.users["A"], "save_squad", p_league=league.id, p_units=league.squad_ids(VALID_SQUAD)
    )
    assert error.code == "BRIEFING_CLOSED"


def test_save_squad_needs_an_active_league_and_membership(db: Db, league: League) -> None:
    db.set_now(T_BRIEFING)
    units = league.squad_ids(VALID_SQUAD)
    assert db.rpc_error(league.outsider, "save_squad", p_league=league.id, p_units=units).code == (
        "NOT_A_MEMBER"
    )
    lobby = make_league(db, start=False)
    assert db.rpc_error(lobby.host, "save_squad", p_league=lobby.id, p_units=units).code == (
        "LEAGUE_NOT_ACTIVE"
    )


# --- swaps ------------------------------------------------------------------------------------
@pytest.fixture
def resupply(league: League) -> League:
    league.save_squad("A")
    league.open_resupply()
    league.db.set_now(T_RESUPPLY)
    return league


def _swap(league: League, slot: str, reserve: str, who: str = "A") -> None:
    league.db.rpc(
        league.users[who], "swap_unit", p_league=league.id, p_slot=slot, p_reserve_slot=reserve
    )


def _swap_error(league: League, slot: str, reserve: str, who: str = "A") -> str:
    return league.db.rpc_error(
        league.users[who], "swap_unit", p_league=league.id, p_slot=slot, p_reserve_slot=reserve
    ).code


def _swaps(league: League, who: str = "A") -> dict[str, str]:
    rows = league.db.fetch_admin(
        "select slot::text, reserve_slot::text from public.swaps where member_id = %s",
        (league.members[who],),
    )
    return {row["slot"]: row["reserve_slot"] for row in rows}


def test_swap_can_be_scheduled_replaced_and_cancelled(resupply: League) -> None:
    _swap(resupply, "marksman", "reserve_2")  # MSFT (US) -> JPM (US)
    _swap(resupply, "marksman", "reserve_1")  # replaced: -> BNP.PA (EU)
    assert _swaps(resupply) == {"marksman": "reserve_1"}
    resupply.db.rpc(resupply.users["A"], "cancel_swap", p_league=resupply.id, p_slot="marksman")
    assert _swaps(resupply) == {}
    error = resupply.db.rpc_error(
        resupply.users["A"], "cancel_swap", p_league=resupply.id, p_slot="marksman"
    )
    assert error.code == "NO_SUCH_SWAP"


@pytest.mark.parametrize(
    ("slot", "reserve", "code"),
    [
        ("reserve_1", "reserve_2", "SWAP_INVALID_SLOT"),
        ("marksman", "reserve_3", "RESERVE_SLOT_EMPTY"),
        ("marksman", "champion", "RESERVE_SLOT_EMPTY"),
        ("saboteur", "reserve_2", "FRONT_NEEDS_REGION"),  # SAP.DE (EU) -> JPM (US): 1 EU left
        ("champion", "reserve_1", "VETERAN_SAME_REGION"),  # AAPL -> BNP.PA, veteran MC.PA is EU
        ("priority_target", "reserve_2", "PRIORITY_TARGET_NOT_IN_ZONE"),
    ],
)
def test_swap_rejections(resupply: League, slot: str, reserve: str, code: str) -> None:
    assert _swap_error(resupply, slot, reserve) == code


def test_swap_limit_and_quartermaster(db: Db) -> None:
    league = make_league(db, {"A": "quartermaster", "B": "bastion"})
    league.save_squad("A", {**VALID_SQUAD, "reserve_3": "KO"})
    league.save_squad("B")
    league.open_resupply()
    db.set_now(T_RESUPPLY)
    _swap(league, "marksman", "reserve_2")
    error = league.db.rpc_error(
        league.users["A"],
        "swap_unit",
        p_league=league.id,
        p_slot="veteran",
        p_reserve_slot="reserve_2",
    )
    assert error.code == "RESERVE_ALREADY_USED"
    _swap(league, "veteran", "reserve_1")  # MC.PA -> BNP.PA, both EU: 2 swaps allowed
    assert _swap_error(league, "champion", "reserve_3") == "SWAP_LIMIT"
    _swap(league, "marksman", "reserve_1", who="B")
    error = league.db.rpc_error(
        league.users["B"],
        "swap_unit",
        p_league=league.id,
        p_slot="champion",
        p_reserve_slot="reserve_2",
    )
    assert (error.code, error.vars) == ("SWAP_LIMIT", {"max": 1})


def test_cancel_swap_keeps_the_front_valid(db: Db) -> None:
    league = make_league(db, {"A": "quartermaster"})
    league.save_squad(
        "A", {**VALID_SQUAD, "reserve_1": "KO", "reserve_2": "BNP.PA", "reserve_3": "AIR.PA"}
    )
    league.open_resupply()
    db.set_now(T_RESUPPLY)
    _swap(league, "marksman", "reserve_2")  # MSFT (US) -> BNP.PA (EU): 3 EU
    _swap(league, "saboteur", "reserve_1")  # SAP.DE (EU) -> KO (US): 2 EU, valid with the first
    error = db.rpc_error(league.users["A"], "cancel_swap", p_league=league.id, p_slot="marksman")
    assert error.code == "FRONT_NEEDS_REGION"  # cancelling the first would leave 1 EU
    db.rpc(league.users["A"], "cancel_swap", p_league=league.id, p_slot="saboteur")
    db.rpc(league.users["A"], "cancel_swap", p_league=league.id, p_slot="marksman")
    assert _swaps(league) == {}


@pytest.mark.parametrize("when", ["briefing", "before_open", "after_close", "not_opened"])
def test_swaps_only_during_resupply(db: Db, league: League, when: str) -> None:
    league.save_squad("A")
    if when != "not_opened":
        league.open_resupply()
    db.set_now(
        {
            "briefing": T_BRIEFING,
            "before_open": RESUPPLY_OPENS_AT.replace(minute=4),
            "after_close": RESUPPLY_CLOSES_AT.replace(second=59, minute=59),
            "not_opened": T_RESUPPLY,
        }[when]
    )
    assert _swap_error(league, "marksman", "reserve_2") == "RESUPPLY_CLOSED"


def test_swap_needs_a_squad_and_no_blockade(db: Db, league: League) -> None:
    league.open_resupply()
    db.set_now(T_RESUPPLY)
    assert _swap_error(league, "marksman", "reserve_2", who="B") == "NO_SQUAD"
    league.save_squad("A")
    league.apply_order("B", "blockade", "A")
    db.set_now(T_RESUPPLY)
    assert _swap_error(league, "marksman", "reserve_2") == "BLOCKADED"
