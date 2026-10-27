"""Orders (GAME_RULES §6) and pacts (§7)."""

import pytest
from conftest import (
    OTHER_SQUAD,
    PREV_WEEK,
    T_AFTER_LOCK,
    T_BRIEFING,
    T_RESUPPLY,
    VALID_SQUAD,
    WEEK,
    Db,
    League,
    make_league,
)


@pytest.fixture
def armed(db: Db) -> League:
    league = make_league(db, {"A": "bastion", "B": "hunter", "C": "berserker", "D": "shadow"})
    for name in ("A", "B", "C", "D"):
        league.give_ammo(name, 5)
    league.save_squad("A")
    league.save_squad("B", OTHER_SQUAD)
    return league


def _order(
    league: League, who: str, order_type: str, target: str | None = None, slot: str | None = None
) -> object:
    params: dict[str, object] = {"p_league": league.id, "p_type": order_type}
    if target is not None:
        params["p_target_member"] = league.members[target]
    if slot is not None:
        params["p_target_slot"] = slot
    return league.db.rpc(league.users[who], "play_order", **params)


def _order_error(
    league: League, who: str, order_type: str, target: str | None = None, slot: str | None = None
) -> str:
    params: dict[str, object] = {"p_league": league.id, "p_type": order_type}
    if target is not None:
        params["p_target_member"] = league.members[target]
    if slot is not None:
        params["p_target_slot"] = slot
    return league.db.rpc_error(league.users[who], "play_order", **params).code


def _balance(league: League, who: str) -> int:
    return league.db.fetch_admin(
        "select coalesce(sum(delta), 0)::int as b from public.ammo_ledger where member_id = %s",
        (league.members[who],),
    )[0]["b"]


def test_order_is_validated_and_paid(db: Db, armed: League) -> None:
    db.set_now(T_BRIEFING)
    order_id = _order(armed, "A", "jamming", "B")
    order = db.fetch_admin("select * from public.orders where id = %s", (order_id,))[0]
    assert (order["status"], order["order_window"], order["cost"]) == ("pending", "briefing", 1)
    assert order["resolved_at"] is None
    assert _balance(armed, "A") == 4


def test_order_windows(db: Db, armed: League) -> None:
    db.set_now(T_AFTER_LOCK)
    assert _order_error(armed, "A", "jamming", "B") == "ORDER_WINDOW_CLOSED"
    db.set_now(T_BRIEFING)
    assert _order_error(armed, "A", "pillage", "B") == "ORDER_WRONG_WINDOW"
    armed.open_resupply()
    db.set_now(T_RESUPPLY)
    assert _order_error(armed, "A", "blockade", "B") == "ORDER_WRONG_WINDOW"
    assert _order_error(armed, "A", "intel", "B") == "ORDER_WRONG_WINDOW"
    _order(armed, "A", "pillage", "B")


def test_berserker_cannot_defend(db: Db, armed: League) -> None:
    db.set_now(T_BRIEFING)
    assert _order_error(armed, "C", "force_field") == "COMMANDER_FORBIDS_ORDER"
    armed.open_resupply()
    db.set_now(T_RESUPPLY)
    assert (
        _order_error(armed, "C", "tactical_retreat", slot="champion") == "COMMANDER_FORBIDS_ORDER"
    )


def test_once_per_week_orders(db: Db, armed: League) -> None:
    armed.open_resupply()
    db.set_now(T_RESUPPLY)
    _order(armed, "A", "reversal")
    assert _order_error(armed, "A", "reversal") == "ORDER_ONCE_PER_WEEK"


def test_blockaded_player_cannot_play_resupply_orders(db: Db, armed: League) -> None:
    armed.apply_order("B", "blockade", "A")
    armed.open_resupply()
    db.set_now(T_RESUPPLY)
    assert _order_error(armed, "A", "force_field") == "BLOCKADED"


def test_targets(db: Db, armed: League) -> None:
    db.set_now(T_BRIEFING)
    assert _order_error(armed, "A", "jamming") == "TARGET_REQUIRED"
    assert _order_error(armed, "A", "jamming", "A") == "INVALID_TARGET"
    assert _order_error(armed, "A", "jamming", "Drone") == "INVALID_TARGET"
    other = make_league(db)
    params = {"p_league": armed.id, "p_type": "jamming", "p_target_member": other.members["B"]}
    assert db.rpc_error(armed.users["A"], "play_order", **params).code == "INVALID_TARGET"
    assert _order_error(armed, "A", "intel", "D") == "TARGET_IMMUNE_TO_INTEL"
    assert _order_error(armed, "A", "force_field", "B") == "TARGET_NOT_ALLOWED"
    assert _order_error(armed, "A", "jamming", "B", slot="champion") == "TARGET_SLOT_NOT_ALLOWED"
    armed.open_resupply()
    db.set_now(T_RESUPPLY)
    assert _order_error(armed, "A", "orbital_strike", "B") == "TARGET_SLOT_REQUIRED"
    assert (
        _order_error(armed, "A", "orbital_strike", "B", slot="reserve_1") == "TARGET_SLOT_INVALID"
    )
    assert _order_error(armed, "A", "field_promotion", slot="champion") == "TARGET_SLOT_INVALID"
    _order(armed, "A", "field_promotion", slot="marksman")
    _order(armed, "A", "orbital_strike", "B", slot="champion")


def test_attack_cap_rejects_the_third_attack_without_charging(db: Db, armed: League) -> None:
    db.set_now(T_BRIEFING)
    _order(armed, "A", "jamming", "B")
    _order(armed, "C", "blockade", "B")
    before = _balance(armed, "D")
    error = db.rpc_error(
        armed.users["D"],
        "play_order",
        p_league=armed.id,
        p_type="jamming",
        p_target_member=armed.members["B"],
    )
    assert (error.code, error.vars) == ("ATTACK_CAP_REACHED", {"max": 2})
    assert _balance(armed, "D") == before
    _order(armed, "D", "jamming", "A")  # another target is fine


def test_bounty_discount_on_the_strict_leader(db: Db, armed: League) -> None:
    db.exec_admin(
        "insert into public.weeks (league_id, week, number, lock_at, resupply_closes_at) "
        "values (%s, %s, 0, now(), now())",
        (armed.id, PREV_WEEK),
    )
    for name, points in (("A", 5), ("B", 10), ("C", 2), ("D", 0)):
        db.exec_admin(
            "insert into public.scores_final (league_id, week, member_id, pf_total, pf_picking, "
            "rank, campaign_points) values (%s, %s, %s, 0, 0, 1, %s)",
            (armed.id, PREV_WEEK, armed.members[name], points),
        )
    db.set_now(T_BRIEFING)
    blockade = _order(armed, "A", "blockade", "B")  # cost 2 - 1
    jamming = _order(armed, "C", "jamming", "B")  # cost 1, minimum 1
    costs = db.fetch_admin(
        "select id, cost from public.orders where id = any(%s)", ([blockade, jamming],)
    )
    assert {row["id"]: row["cost"] for row in costs} == {blockade: 1, jamming: 1}
    assert db.fetch_admin(
        "select cost from public.orders where id = %s", (_order(armed, "B", "blockade", "A"),)
    ) == [{"cost": 2}]


def test_no_bounty_on_a_tie(db: Db, armed: League) -> None:
    db.set_now(T_BRIEFING)  # week 1: everybody at 0 points
    order_id = _order(armed, "A", "blockade", "B")
    assert db.fetch_admin("select cost from public.orders where id = %s", (order_id,)) == [
        {"cost": 2}
    ]


def test_not_enough_ammo(db: Db, armed: League) -> None:
    armed.give_ammo("A", -4)
    armed.open_resupply()
    db.set_now(T_RESUPPLY)
    error = db.rpc_error(
        armed.users["A"],
        "play_order",
        p_league=armed.id,
        p_type="pillage",
        p_target_member=armed.members["B"],
    )
    assert (error.code, error.vars) == ("NOT_ENOUGH_AMMO", {"cost": 3, "balance": 1})


def test_intel_resolves_immediately_for_the_attacker_only(db: Db, armed: League) -> None:
    db.set_now(T_BRIEFING)
    order_id = _order(armed, "A", "intel", "B")
    order = db.fetch_admin(
        "select status, resolved_at from public.orders where id = %s", (order_id,)
    )
    assert order == [{"status": "applied", "resolved_at": T_BRIEFING}]
    armed.save_squad("B", VALID_SQUAD)  # B changes the draft afterwards
    events = db.select(
        armed.users["A"], "select template_key, vars from public.events where kind = 'intel'"
    )
    assert len(events) == 1 and events[0]["template_key"] == "event.intel.snapshot"
    assert events[0]["vars"]["units"] == OTHER_SQUAD  # the snapshot does not follow the change
    for name in ("B", "C"):
        assert (
            db.select(armed.users[name], "select 1 from public.events where kind = 'intel'") == []
        )


# --- pacts ------------------------------------------------------------------------------------
def _pacts(league: League) -> dict[tuple[str, str], str]:
    names = {member: name for name, member in league.members.items()}
    rows = league.db.fetch_admin(
        "select proposer_member_id, partner_member_id, status from public.pacts "
        "where league_id = %s",
        (league.id,),
    )
    return {
        (names[r["proposer_member_id"]], names[r["partner_member_id"]]): r["status"] for r in rows
    }


def test_pact_proposal_acceptance_and_cancellation(db: Db, armed: League) -> None:
    db.set_now(T_BRIEFING)
    ab = db.rpc(armed.users["A"], "propose_pact", p_league=armed.id, p_partner=armed.members["B"])
    db.rpc(armed.users["C"], "propose_pact", p_league=armed.id, p_partner=armed.members["B"])
    db.rpc(armed.users["A"], "propose_pact", p_league=armed.id, p_partner=armed.members["D"])
    assert (
        db.rpc_error(
            armed.users["B"], "propose_pact", p_league=armed.id, p_partner=armed.members["A"]
        ).code
        == "PACT_ALREADY_PROPOSED"
    )
    assert db.rpc_error(armed.users["A"], "accept_pact", p_pact=ab).code == "NOT_PACT_PARTNER"
    db.rpc(armed.users["B"], "accept_pact", p_pact=ab)
    assert _pacts(armed) == {("A", "B"): "active", ("C", "B"): "cancelled", ("A", "D"): "cancelled"}
    assert db.rpc_error(armed.users["B"], "accept_pact", p_pact=ab).code == "PACT_NOT_PENDING"
    assert (
        db.rpc_error(
            armed.users["C"], "propose_pact", p_league=armed.id, p_partner=armed.members["A"]
        ).code
        == "PACT_ALREADY_ACTIVE"
    )


def test_pact_decline_and_rejections(db: Db, armed: League) -> None:
    db.set_now(T_BRIEFING)
    pact = db.rpc(armed.users["A"], "propose_pact", p_league=armed.id, p_partner=armed.members["C"])
    db.rpc(armed.users["C"], "decline_pact", p_pact=pact)
    assert _pacts(armed) == {("A", "C"): "declined"}
    for partner in ("A", "Drone"):
        assert (
            db.rpc_error(
                armed.users["A"],
                "propose_pact",
                p_league=armed.id,
                p_partner=armed.members[partner],
            ).code
            == "INVALID_TARGET"
        )
    assert (
        db.rpc_error(
            armed.users["A"], "accept_pact", p_pact="00000000-0000-0000-0000-000000000000"
        ).code
        == "PACT_NOT_FOUND"
    )
    late = db.rpc(armed.users["B"], "propose_pact", p_league=armed.id, p_partner=armed.members["D"])
    db.set_now(T_AFTER_LOCK)
    assert (
        db.rpc_error(
            armed.users["B"], "propose_pact", p_league=armed.id, p_partner=armed.members["C"]
        ).code
        == "BRIEFING_CLOSED"
    )
    assert db.rpc_error(armed.users["D"], "accept_pact", p_pact=late).code == "BRIEFING_CLOSED"


def test_week_number_one_is_used(db: Db, armed: League) -> None:
    db.set_now(T_BRIEFING)
    order_id = _order(armed, "A", "force_field")
    assert db.fetch_admin("select week from public.orders where id = %s", (order_id,)) == [
        {"week": WEEK}
    ]


def _costs(db: Db, league: League, who: str) -> dict[tuple[str, str | None], int]:
    names = {member: name for name, member in league.members.items()}
    rows = db.rpc_rows(league.users[who], "order_costs", p_league=league.id)
    return {
        (r["type"], names.get(r["target_member_id"]) if r["target_member_id"] else None): r["cost"]
        for r in rows
    }


def test_order_costs_match_what_play_order_charges(db: Db, armed: League) -> None:
    db.exec_admin(
        "insert into public.weeks (league_id, week, number, lock_at, resupply_closes_at) "
        "values (%s, %s, 0, now(), now())",
        (armed.id, PREV_WEEK),
    )
    for name, points in (("A", 5), ("B", 10), ("C", 2), ("D", 0)):
        db.exec_admin(
            "insert into public.scores_final (league_id, week, member_id, pf_total, pf_picking, "
            "rank, campaign_points) values (%s, %s, %s, 0, 0, 1, %s)",
            (armed.id, PREV_WEEK, armed.members[name], points),
        )
    db.set_now(T_BRIEFING)
    costs = _costs(db, armed, "A")
    # Briefing window only; targeted orders per other human (never the Drone, never A).
    assert {t for t, _ in costs} == {"blockade", "jamming", "force_field", "intel"}
    assert costs[("blockade", "B")] == 1 and costs[("blockade", "C")] == 2  # B has the Bounty
    assert costs[("force_field", None)] == 1
    assert ("blockade", "A") not in costs and ("blockade", "Drone") not in costs
    rows = db.rpc_rows(armed.users["A"], "order_costs", p_league=armed.id)
    assert {r["target_has_bounty"] for r in rows if r["type"] == "blockade"} == {True, False}
    order_id = _order(armed, "A", "blockade", "B")
    assert db.fetch_admin("select cost from public.orders where id = %s", (order_id,)) == [
        {"cost": costs[("blockade", "B")]}
    ]
    # The Berserker does not see the orders it cannot play.
    assert ("force_field", None) not in _costs(db, armed, "C")


def test_order_costs_follow_the_windows(db: Db, armed: League) -> None:
    armed.open_resupply()
    db.set_now(T_AFTER_LOCK)
    assert _costs(db, armed, "A") == {}
    db.set_now(T_RESUPPLY)
    types = {t for t, _ in _costs(db, armed, "A")}
    assert "orbital_strike" in types and "blockade" not in types
    assert db.rpc_error(armed.outsider, "order_costs", p_league=armed.id).code == "NOT_A_MEMBER"
