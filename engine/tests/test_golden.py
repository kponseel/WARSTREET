"""Golden weeks: 3, 4 and 5 players with swaps, a pact betrayal, a blocked attack and the
Drone. Totals are computed BY HAND in the comments (prices built from round segment
returns, see scenario.RETURNS) and asserted; the full breakdown is frozen in golden/*.json
to catch any regression. Regenerate the JSON only after checking a change by hand:
UPDATE_GOLDEN=1 pytest engine/tests/test_golden.py
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

import pytest
from scenario import instruments, order, player

from engine.models import WeekInput, WeekResult
from engine.scoring import score_week

GOLDEN_DIR = Path(__file__).parent / "golden"


def week_3_players() -> WeekInput:
    """A bastion, B hunter, C prophet. Pact A-B. B's force field blocks A's jamming (A
    betrays B). C strikes A's marksman, which A swapped in (the strike follows the slot).
    C plunders B."""
    return WeekInput(
        players=(
            player(
                "A",
                "bastion",
                (11, 1, 12, 2, 13),
                (3, 14),
                swaps=(("marksman", "reserve_2"),),
                points=10,
                ally="B",
            ),
            player("B", "hunter", (13, 4, 1, 15, 16), (5, 11), points=5, ally="A"),
            player("C", "prophet", (4, 16, 5, 12, 11), (2, 15), points=2),
            player("Drone", None, (3, 14, 15, 5, 13), (1, 16), drone=True),
        ),
        instruments=instruments(),
        orders=(
            order("o1", "B", "force_field", 10),
            order("o2", "A", "jamming", 20, target="B"),
            order("o3", "C", "orbital_strike", 2000, target="A", slot="marksman"),
            order("o4", "C", "pillage", 2010, target="B"),
        ),
    )


def week_4_players_final() -> WeekInput:
    """D berserker, E technomancer, F quartermaster (2 swaps), G shadow; final week (x2).
    Pact E-G. G's two force fields block E's jamming (E betrays G) and D's blockade.
    E: field promotion (veteran) then reversal; D and G strike E's champion (x0.25), so
    G betrays E too.
    F: tactical retreat on the marksman; D and G both plunder F (same base)."""
    return WeekInput(
        players=(
            player("D", "berserker", (20, 7, 18, 17, 1), (4, 19), points=20),
            player("E", "technomancer", (6, 19, 2, 20, 13), (5, 16), points=20, ally="G"),
            player(
                "F",
                "quartermaster",
                (17, 3, 4, 7, 11),
                (1, 12, 14),
                points=12,
                swaps=(("champion", "reserve_2"), ("saboteur", "reserve_1")),
            ),
            player("G", "shadow", (11, 5, 16, 6, 20), (2, 15), points=8, ally="E"),
            player("Drone", None, (2, 15, 3, 19, 13), (4, 18), drone=True),
        ),
        instruments=instruments(),
        orders=(
            order("g1", "G", "force_field", 10),
            order("g2", "G", "force_field", 11),
            order("e1", "E", "jamming", 20, target="G"),
            order("d1", "D", "blockade", 30, target="G"),
            order("f1", "F", "tactical_retreat", 2000, slot="marksman"),
            order("e2", "E", "field_promotion", 2001, slot="veteran"),
            order("e3", "E", "reversal", 2002),
            order("d2", "D", "pillage", 2003, target="F"),
            order("g3", "G", "pillage", 2004, target="F"),
            order("d3", "D", "orbital_strike", 2005, target="E", slot="champion"),
            order("g4", "G", "orbital_strike", 2006, target="E", slot="champion"),
        ),
        is_final=True,
    )


def week_5_players() -> WeekInput:
    """H bastion, I berserker, J prophet, K hunter, L technomancer. Pact H-L: L's force
    field blocks H's jamming (H betrays L). L swaps its marksman. J plunders I."""
    return WeekInput(
        players=(
            player("H", "bastion", (11, 1, 12, 2, 13), (3, 14), points=30, ally="L"),
            player("I", "berserker", (13, 4, 1, 15, 16), (5, 11), points=25),
            player("J", "prophet", (4, 16, 5, 12, 11), (2, 15), points=20),
            player("K", "hunter", (4, 16, 5, 12, 11), (2, 15), points=10),
            player(
                "L",
                "technomancer",
                (11, 1, 12, 2, 13),
                (3, 14),
                points=5,
                ally="H",
                swaps=(("marksman", "reserve_2"),),
            ),
            player("Drone", None, (3, 14, 16, 15, 13), (1, 20), drone=True),
        ),
        instruments=instruments(),
        orders=(
            order("l1", "L", "force_field", 10),
            order("h1", "H", "jamming", 20, target="L"),
            order("j1", "J", "pillage", 2000, target="I"),
        ),
    )


def _totals(result: WeekResult) -> dict[str, int]:
    return {m: r.pf_total for m, r in result.players.items()}


def test_golden_3_players_by_hand() -> None:
    result = score_week(week_3_players())
    # A slots: champion 11: 10*2*4 + 10*2*(-1) = 60; veteran 1: 30 + 15 = 45;
    # marksman: S1 unit 12: -30, S2 swapped-in 14 under a strike: 10*1*3*0.5 = 15 -> -15;
    # saboteur 2: 10 + 20 = 30; priority target 13: 60 + 60 = 120. Picking 240.
    # Elite: only A holds 2 -> +10. Perfect shot: 13 (10.25 %) held by A and B -> +40.
    # Bastion: worst slot -15 -> +4. Betrayal -40. Total 240 + 10 + 40 + 4 - 40 = 254.
    # B: champion 13: 100 + 100 = 200 -> clamped 150; veteran 4: 0 + 60; marksman 1: 20 + 10;
    # saboteur 15: 20 + 20; priority 16: 24 + 24. Picking 328. Elite 15 +10, perfect shot +40,
    # total victory +60. Pillage by C: S2 sum 100+60+10+20+24 = 214 -> round(64.2) = 64.
    # Steps 1-8: 328 + 10 + 40 + 60 - 64 = 374; Hunter: A (10 pts > 5) outscored -> +6 = 380.
    # C (saboteur x-2): champion 4: 0 + 80; veteran 16: 30 + 30; marksman 5: 10 + 10;
    # saboteur 12: 60 - 40 = 20; priority 11: 48 - 12 = 36. Picking 216. Elite 5 +10,
    # total victory +60, pillage +64 -> 350.
    # Drone: 30 + 60 - 40 - 20 + 120 = 150.
    assert _totals(result) == {"A": 254, "B": 380, "C": 350, "Drone": 150}
    assert {m: r.pf_picking for m, r in result.players.items()} == {
        "A": 240,
        "B": 328,
        "C": 216,
        "Drone": 150,
    }
    assert {m: (r.rank, r.campaign_points) for m, r in result.players.items()} == {
        "A": (3, 2.0),
        "B": (1, 10.0),
        "C": (2, 5.0),
        "Drone": (None, 0.0),
    }
    assert result.players["A"].badges == ("traitor",)
    assert result.players["B"].badges == ("warlord",)
    assert result.orders.status == {
        "o1": "applied",
        "o2": "blocked",
        "o3": "applied",
        "o4": "applied",
    }


def test_golden_4_players_by_hand() -> None:
    result = score_week(week_4_players_final())
    # D (champion x3): 20: 180 + 120 = 300 -> 150; 7: 60 + 45 = 105; 18: 10 - 10 = 0;
    # saboteur 17: 60 + 60 = 120; priority 1: 24 + 12 = 36. Picking 411.
    # Elite 18 and 1 (+20), resurrection on 7 (prev -8 %, week +7.12 %) +40, pillage +5 -> 476.
    # E: S2 champion/veteran multipliers swapped (1.5 / 2), marksman -1, champion x0.25.
    # champion 6: -160 + 10*1.5*(-5)*0.25 = -178.75 -> -179 -> -150; veteran 19: 0;
    # marksman 2: -10 + 20 = 10; saboteur 20: -60 - 40 = -100; priority 13: 120. Picking -120.
    # Elite 19, 2, 13 (+30), perfect shot 13 (+40), heavy losses on 6 (-40), betrayal (-40)
    # -> -130.
    # F swaps champion <- 12, saboteur <- 1; retreat on the marksman.
    # champion: 17 S1 -120, 12 S2 +40 -> -80; veteran 3 (coef 0.5): 22.5 -> 23; marksman 4: 0;
    # saboteur: 7 S1 -40, 1 S2 -10 -> -50; priority 11: 48 - 12 = 36. Picking -71.
    # Elite 3, 4 (+20), heavy losses on 17 (front at lock) -40. S2 sum 40+0+0-10-12 = 18:
    # two pillages of round(5.4) = 5 -> -10. Total -101.
    # G: 60 + 30 + 40 + 130 + 120 = 380; elite 5, 16 (+20), total victory +60, pillage +5,
    # and G's orbital strike hits E, G's own ally: betrayal -40 -> 425.
    # Drone: -60 - 60 + 15 + 0 + 120 = 15. Final week: points x2.
    assert _totals(result) == {"D": 476, "E": -130, "F": -101, "G": 425, "Drone": 15}
    assert {m: r.campaign_points for m, r in result.players.items() if m != "Drone"} == {
        "D": 20.0,
        "G": 12.0,
        "F": 6.0,
        "E": 2.0,
    }
    assert result.players["D"].badges == ("warlord", "oracle")
    assert result.players["E"].badges == ("cannon_fodder", "traitor", "rusty")
    assert result.players["F"].badges == ("rusty",)
    assert result.players["G"].badges == ("oracle", "traitor")
    assert result.orders.betrayers == frozenset({"E", "G"})
    assert result.orders.status["e1"] == "blocked" and result.orders.status["d1"] == "blocked"
    assert result.orders.status["g1"] == "applied" and result.orders.status["g2"] == "applied"


def test_golden_5_players_by_hand() -> None:
    result = score_week(week_5_players())
    # H: 60 + 45 + (-30 + 20) + 30 + 120 = 245; perfect shot +40, bastion +4 (worst slot
    # -10), betrayal -40 -> 249.
    # I (champion x3): 13: 150 + 150 -> 150; then 60 + 30 + 40 + 48 = 328; elite 15 +10,
    # perfect shot +40, total victory +60; plundered: S2 150+60+10+20+24 = 264 ->
    # round(79.2) = 79 -> 359.
    # J: 216 (as C in the 3-player week) + total victory 60 + pillage 79 = 355.
    # K (hunter, saboteur x-1): 80 + 60 + 20 + (30 - 20) + 36 = 206, total victory 60 -> 266;
    # more points than K: H, I, J; K outscores only H -> +6 = 272.
    # L: 60 + 45 + (-30 + 30) + 30 + 120 = 255 (marksman swapped to 14), perfect shot +40 -> 295.
    # Drone: 30 + 60 + 40 + 40 + 120 = 290 -> rusty for H, J, K, L.
    assert _totals(result) == {"H": 249, "I": 359, "J": 355, "K": 272, "L": 295, "Drone": 290}
    assert {m: r.campaign_points for m, r in result.players.items() if m != "Drone"} == {
        "I": 10.0,
        "J": 7.0,
        "L": 5.0,
        "K": 3.0,
        "H": 1.0,
    }
    assert result.players["K"].breakdown["hunter"] == {"pf": 6, "victims": ["H"]}
    assert [m for m, r in result.players.items() if "rusty" in r.badges] == ["H", "J", "K", "L"]


def _serialise(result: WeekResult) -> dict[str, object]:
    return {
        "players": {m: asdict(r) for m, r in sorted(result.players.items())},
        "orders": {
            "status": dict(sorted(result.orders.status.items())),
            "betrayers": sorted(result.orders.betrayers),
        },
    }


@pytest.mark.parametrize(
    ("name", "build"),
    [
        ("week_3_players", week_3_players),
        ("week_4_players_final", week_4_players_final),
        ("week_5_players", week_5_players),
    ],
)
def test_golden_breakdowns_are_frozen(name: str, build: object) -> None:
    result = _serialise(score_week(build()))  # type: ignore[operator]
    path = GOLDEN_DIR / f"{name}.json"
    if os.environ.get("UPDATE_GOLDEN") == "1":
        GOLDEN_DIR.mkdir(exist_ok=True)
        path.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert json.loads(json.dumps(result)) == expected
