"""score_week on small scenarios: every step of GAME_RULES §4 and the §12 edge cases."""

from dataclasses import replace

from scenario import instruments, order, player

from engine.models import InstrumentWeek, WeekInput
from engine.scoring import score_week

BASE = (11, 1, 12, 2, 13)  # US, EU, US, EU, US
OTHER = (13, 4, 1, 15, 16)
THIRD = (4, 16, 5, 12, 11)


def week(*players, orders=(), insts=None, final=False) -> WeekInput:  # type: ignore[no-untyped-def]
    return WeekInput(
        players=tuple(players),
        instruments=insts or instruments(),
        orders=tuple(orders),
        is_final=final,
    )


def three(**kwargs):  # type: ignore[no-untyped-def]
    return (
        player("A", "technomancer", BASE, (3, 14), **kwargs),
        player("B", "technomancer", OTHER, (5, 11)),
        player("C", "technomancer", THIRD, (2, 15)),
    )


def slot(result, member, name):  # type: ignore[no-untyped-def]
    return result.players[member].breakdown["slots"][name]


def test_unit_pf_uses_slot_multiplier_and_coefficient() -> None:
    insts = instruments()
    insts[1] = replace(insts[1], coef=2.0)
    result = score_week(week(*three(), insts=insts))
    assert slot(result, "A", "veteran")["pf"] == 90  # (2 + 1) % * 10 * 1.5 * 2
    assert slot(result, "A", "saboteur")["pf"] == 30  # -1 * (-1 - 2) * 10


def test_clamp_applies_per_slot() -> None:
    insts = instruments()
    insts[11] = InstrumentWeek(11, "US", p0=100, p_mid=110, p_end=121)  # +10 % then +10 %
    result = score_week(week(*three(), insts=insts))
    champion = slot(result, "A", "champion")
    assert champion["raw"] == 400 and champion["pf"] == 150 and champion["clamped"]


def test_missing_segment_scores_zero_and_is_flagged() -> None:
    insts = instruments()
    insts[11] = replace(insts[11], p_end=None)
    result = score_week(week(*three(), insts=insts))
    champion = slot(result, "A", "champion")
    assert champion["s2"]["missing"] and champion["s2"]["pf"] == 0 and champion["pf"] == 80
    insts.pop(12)
    result = score_week(week(*three(), insts=insts))
    assert (
        slot(result, "A", "marksman")["s1"]["missing"] and slot(result, "A", "marksman")["pf"] == 0
    )


def test_swap_scores_s1_out_and_s2_in_and_is_clamped_as_one_slot() -> None:
    result = score_week(week(*three(swaps=(("marksman", "reserve_2"),))))
    marksman = slot(result, "A", "marksman")
    assert marksman["s1"]["instrument_id"] == 12 and marksman["s2"]["instrument_id"] == 14
    assert marksman["pf"] == 0  # -30 + 30
    assert marksman["swapped_from"] == "reserve_2"


def test_blockade_cancels_swaps() -> None:
    players = three(swaps=(("marksman", "reserve_2"),))
    result = score_week(week(*players, orders=[order("b", "B", "blockade", 1, target="A")]))
    assert slot(result, "A", "marksman")["s2"]["instrument_id"] == 12


def test_orbital_strike_follows_the_slot_after_a_swap() -> None:
    players = three(swaps=(("marksman", "reserve_2"),))
    orders = [order("s", "B", "orbital_strike", 2000, target="A", slot="marksman")]
    marksman = slot(score_week(week(*players, orders=orders)), "A", "marksman")
    assert marksman["s2"]["instrument_id"] == 14 and marksman["s2"]["modifier"] == 0.5
    assert marksman["orders"] == ["orbital_strike"]


def test_elite_units_are_unique_human_fronts() -> None:
    drone = player("Drone", None, (2, 14, 15, 5, 13), (3, 20), drone=True)
    result = score_week(week(*three(), drone))
    # A: 11 (also C), 1 (also B), 12 (also C), 2 (only A, the Drone does not count), 13 (also B)
    assert result.players["A"].breakdown["elite"] == {"instruments": [2], "pf": 10}


def test_pillage_needs_a_positive_base_and_uses_the_same_base_twice() -> None:
    orders = [
        order("p1", "B", "pillage", 2000, target="A"),
        order("p2", "C", "pillage", 2001, target="A"),
    ]
    result = score_week(week(*three(), orders=orders))
    lines = result.players["A"].breakdown["pillage"]
    # A's S2 sum: champion -20, veteran 15, marksman 20, saboteur 20, priority 60 = 95
    assert [line["pf"] for line in lines] == [-29, -29]  # round(28.5) = 29 each
    insts = instruments()
    for i in BASE:
        insts[i] = replace(insts[i], p_end=insts[i].p_mid * 0.9)  # every S2 -10 %
    result = score_week(week(*three(), orders=orders[:1], insts=insts))
    # S2 sum: champion -200, veteran -150, marksman -100, saboteur +100, priority -120 < 0
    assert [line["pf"] for line in result.players["A"].breakdown["pillage"]] == [0]


def test_blocked_pillage_takes_nothing() -> None:
    orders = [order("ff", "A", "force_field", 1), order("p", "B", "pillage", 2000, target="A")]
    result = score_week(week(*three(), orders=orders))
    assert result.players["A"].breakdown["pillage"] == []


def test_betrayal_is_once_per_week() -> None:
    players = (
        player("A", "technomancer", BASE, (3, 14), ally="B"),
        player("B", "technomancer", OTHER, (5, 11), ally="A"),
        player("C", "technomancer", THIRD, (2, 15)),
    )
    orders = [
        order("j", "A", "jamming", 1, target="B"),
        order("s", "A", "orbital_strike", 2000, target="B", slot="champion"),
    ]
    result = score_week(week(*players, orders=orders))
    assert result.players["A"].breakdown["betrayal"] == -40
    assert "traitor" in result.players["A"].badges and "traitor" not in result.players["B"].badges


def test_ties_share_campaign_points() -> None:
    players = (
        player("A", "technomancer", BASE, (3, 14)),
        player("B", "technomancer", BASE, (3, 14)),
        player("C", "technomancer", THIRD, (2, 15)),
    )
    result = score_week(week(*players))
    a, b, c = result.players["A"], result.players["B"], result.players["C"]
    assert c.rank == 1 and "warlord" in c.badges
    assert a.pf_total == b.pf_total and a.rank == b.rank == 2
    assert a.campaign_points == b.campaign_points == 3.5  # (5 + 2) / 2


def test_tied_winners_are_both_warlords() -> None:
    players = (
        player("A", "technomancer", OTHER, (3, 14)),
        player("B", "technomancer", OTHER, (3, 14)),
        player("C", "technomancer", BASE, (2, 15)),
    )
    result = score_week(week(*players))
    a, b = result.players["A"], result.players["B"]
    assert a.rank == b.rank == 1 and a.campaign_points == b.campaign_points == 7.5  # (10 + 5) / 2
    assert "warlord" in a.badges and "warlord" in b.badges


def test_drone_is_scored_but_not_ranked() -> None:
    drone = player("Drone", "bastion", BASE, (3, 14), drone=True)  # a commander is ignored
    result = score_week(week(*three(), drone, final=True))
    d = result.players["Drone"]
    assert d.rank is None and d.campaign_points == 0 and d.badges == ()
    assert d.pf_total == d.pf_picking == 245
    assert set(d.breakdown) == {"slots", "pf_picking", "pf_total"}
    assert sorted(r.campaign_points for m, r in result.players.items() if m != "Drone") == [
        4,
        10,
        20,
    ]


def test_pillage_by_or_on_unknown_players_is_ignored() -> None:
    orders = [
        order("p", "Z", "pillage", 2000, target="A"),
        order("q", "A", "pillage", 2001, target="Z"),
    ]
    result = score_week(week(*three(), orders=orders))
    assert result.players["A"].breakdown["pillage"] == []
