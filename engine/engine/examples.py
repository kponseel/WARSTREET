"""Worked examples for the in-app tutorial, computed by the real scoring engine.

The tutorial explains War Points and the commanders with concrete numbers. Those numbers
must never be computed by the frontend (CLAUDE.md: game maths only in engine/), so they
are computed here from a small made-up week and written to
web/src/content/examples.generated.ts by supabase/scripts/generate_seed.py (checked in
CI like the seed). Changing a value in config.py changes the examples with it.

Pure functions, no I/O. Units are fictional companies: the examples are not market data.
"""

from __future__ import annotations

from collections.abc import Mapping

from engine.commanders import hunter_bonus
from engine.models import InstrumentWeek, PlayerWeek, Swap, WeekInput
from engine.scoring import score_week

ME = "you"

# id -> (name, region, Mon-Wed move %, Thu-Fri move %). Every unit has coef 1.0.
UNITS: Mapping[int, tuple[str, str, float, float]] = {
    1: ("Orion Robotics", "US", 4.0, 0.0),
    2: ("Lumen Luxe", "EU", 2.0, 0.0),
    3: ("Petra Energy", "EU", -3.0, 0.0),
    4: ("Volt Motors", "US", -5.0, 0.0),
    5: ("Aero Union", "EU", 3.0, 0.0),
    6: ("Nord Software", "EU", 0.0, 0.0),
    7: ("Pacific Foods", "US", 0.0, 0.0),
    8: ("Delta Shipping", "EU", 0.0, 0.0),
    # The rivals' squad, so the week has a ranking.
    11: ("Rival A", "US", 1.0, 0.0),
    12: ("Rival B", "EU", 1.0, 0.0),
    13: ("Rival C", "EU", 0.0, 0.0),
    14: ("Rival D", "US", 0.0, 0.0),
    15: ("Rival E", "EU", 1.0, 0.0),
    16: ("Rival F", "EU", 0.0, 0.0),
    17: ("Rival G", "US", 0.0, 0.0),
}

SQUAD: Mapping[str, int] = {
    "champion": 1,
    "veteran": 2,
    "marksman": 3,
    "saboteur": 4,
    "priority_target": 5,
    "reserve_1": 6,
    "reserve_2": 7,
}
RIVAL_SQUAD: Mapping[str, int] = {
    "champion": 11,
    "veteran": 12,
    "marksman": 13,
    "saboteur": 14,
    "priority_target": 15,
    "reserve_1": 16,
    "reserve_2": 17,
}

# Thursday swap example: on Thursday morning two front units start losing.
THURSDAY_MOVES: Mapping[int, tuple[float, float]] = {
    2: (2.0, -2.0),  # Lumen Luxe (Veteran)
    3: (-3.0, -3.0),  # Petra Energy (Marksman)
    6: (0.0, 2.0),  # Nord Software (reserve)
    8: (0.0, 2.0),  # Delta Shipping (the Quartermaster's third reserve)
}


def _instruments(
    overrides: Mapping[int, tuple[float, float]] | None = None,
) -> dict[int, InstrumentWeek]:
    out: dict[int, InstrumentWeek] = {}
    for unit_id, (_name, region, s1, s2) in UNITS.items():
        if overrides and unit_id in overrides:
            s1, s2 = overrides[unit_id]
        p0 = 100.0
        p_mid = p0 * (1 + s1 / 100)
        out[unit_id] = InstrumentWeek(
            unit_id, region, p0, p_mid, p_mid * (1 + s2 / 100), coef=1.0, prev_week_return=0.0
        )
    return out


def _score(
    commander: str | None,
    *,
    squad: Mapping[str, int] = SQUAD,
    swaps: tuple[Swap, ...] = (),
    overrides: Mapping[int, tuple[float, float]] | None = None,
) -> dict[str, object]:
    week = WeekInput(
        players=(
            PlayerWeek(ME, commander, squad, swaps),
            # Two rivals: a league has at least three players.
            PlayerWeek("rival_1", None, RIVAL_SQUAD),
            PlayerWeek("rival_2", None, RIVAL_SQUAD),
        ),
        instruments=_instruments(overrides),
    )
    return score_week(week).players[ME].breakdown


def _slot_pf(breakdown: Mapping[str, object], slot: str) -> int:
    slots = breakdown["slots"]
    assert isinstance(slots, dict)
    value = slots[slot]["pf"]
    assert isinstance(value, int)
    return value


def _unit(slot: str) -> dict[str, object]:
    unit_id = SQUAD[slot]
    name, region, s1, s2 = UNITS[unit_id]
    return {"slot": slot, "name": name, "region": region, "move": s1 + s2}


def build_examples() -> dict[str, object]:
    """Every number the tutorial shows, keyed for the web app (flat names, integers)."""
    base = _score(None)
    week = [{**_unit(slot), "pf": _slot_pf(base, slot)} for slot in SQUAD if "reserve" not in slot]

    bastion = _score("bastion")
    berserker = _score("berserker")
    berserker_down = _score("berserker", overrides={1: (-4.0, 0.0)})
    plain_down = _score(None, overrides={1: (-4.0, 0.0)})
    prophet = _score("prophet")
    prophet_up = _score("prophet", overrides={4: (5.0, 0.0)})
    plain_up = _score(None, overrides={4: (5.0, 0.0)})

    # Thursday: everyone may swap once; the Quartermaster twice (third reserve unit).
    thursday = _score(None, overrides=THURSDAY_MOVES)
    one_swap = _score(None, swaps=(Swap("marksman", "reserve_1"),), overrides=THURSDAY_MOVES)
    qm_squad = {**SQUAD, "reserve_3": 8}
    qm_swaps = (Swap("marksman", "reserve_1"), Swap("veteran", "reserve_3"))
    two_swaps = _score("quartermaster", squad=qm_squad, swaps=qm_swaps, overrides=THURSDAY_MOVES)

    # Hunter: you are 3rd in the campaign, behind two players, and beat both this week.
    points_before = {ME: 4.0, "first": 15.0, "second": 12.0}
    hunter_both, _ = hunter_bonus(ME, {ME: 200, "first": 150, "second": 180}, points_before)
    hunter_one, _ = hunter_bonus(ME, {ME: 200, "first": 230, "second": 180}, points_before)

    bastion_line = bastion["bastion"]
    assert isinstance(bastion_line, int)
    marksman = _unit("marksman")
    champion = _unit("champion")
    saboteur = _unit("saboteur")
    return {
        "week": week,
        "weekUnitsTotal": sum(_slot_pf(base, slot) for slot in SQUAD if "reserve" not in slot),
        "bastionUnit": marksman["name"],
        "bastionMove": marksman["move"],
        "bastionBefore": _slot_pf(base, "marksman"),
        "bastionAfter": _slot_pf(base, "marksman") + bastion_line,
        "berserkerUnit": champion["name"],
        "berserkerMove": champion["move"],
        "berserkerBefore": _slot_pf(base, "champion"),
        "berserkerAfter": _slot_pf(berserker, "champion"),
        "berserkerDownBefore": _slot_pf(plain_down, "champion"),
        "berserkerDownAfter": _slot_pf(berserker_down, "champion"),
        "prophetUnit": saboteur["name"],
        "prophetMove": saboteur["move"],
        "prophetBefore": _slot_pf(base, "saboteur"),
        "prophetAfter": _slot_pf(prophet, "saboteur"),
        "prophetUpBefore": _slot_pf(plain_up, "saboteur"),
        "prophetUpAfter": _slot_pf(prophet_up, "saboteur"),
        "hunterBoth": hunter_both,
        "hunterOne": hunter_one,
        "swapOut": UNITS[SQUAD["marksman"]][0],
        "swapIn": UNITS[SQUAD["reserve_1"]][0],
        "swapBefore": _slot_pf(thursday, "marksman"),
        "swapAfter": _slot_pf(one_swap, "marksman"),
        "qmSwapOut": UNITS[SQUAD["veteran"]][0],
        "qmSwapIn": UNITS[8][0],
        "qmBefore": _slot_pf(thursday, "veteran"),
        "qmAfter": _slot_pf(two_swaps, "veteran"),
    }
