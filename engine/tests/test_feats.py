"""Feats and badges."""

from engine.feats import badges, best_long_instruments, feats

FRONT = {"champion": 1, "veteran": 2, "marksman": 3, "saboteur": 4, "priority_target": 5}
POSITIVE = {s: 10 for s in FRONT}


def test_best_long_instruments_ignore_saboteurs_and_missing_data() -> None:
    fronts = {"A": FRONT, "B": {**FRONT, "saboteur": 9, "champion": 6}}
    returns = {1: 3.0, 2: 1.0, 3: None, 4: 50.0, 5: 3.0, 6: -1.0, 9: 99.0}
    assert best_long_instruments(fronts, returns) == {1, 5}
    assert best_long_instruments({}, returns) == set()


def codes(won: list[dict[str, object]]) -> list[str]:
    return [str(w["code"]) for w in won]


def test_total_victory_and_perfect_shot_once() -> None:
    won = feats(FRONT, POSITIVE, {}, {}, best={1, 5})
    assert codes(won) == ["total_victory", "perfect_shot"]  # perfect shot once with two
    assert codes(feats(FRONT, {**POSITIVE, "saboteur": 0}, {}, {}, best={4})) == []


def test_resurrection_once_and_heavy_losses_per_long_unit() -> None:
    returns = {1: 4.5, 2: 5.0, 3: -10.5, 4: -20.0, 5: -11.0}
    prev = {1: -6.5, 2: -7.0, 4: -9.0}
    won = feats(FRONT, {**POSITIVE, "champion": -1}, returns, prev, best=set())
    assert codes(won) == ["resurrection", "heavy_losses", "heavy_losses"]  # saboteur 4 excluded
    assert feats(FRONT, POSITIVE, {1: 4.0}, {1: -6.5}, set())[0]["code"] == "total_victory"
    assert codes(feats(FRONT, POSITIVE, {1: 4.0}, {1: -6.5}, set())) == ["total_victory"]


def test_badges() -> None:
    slot_pf = {"champion": -1, "veteran": -2, "marksman": -3, "saboteur": -4, "priority_target": -5}
    got = badges(
        FRONT, slot_pf, {1: -5.5}, {1: -6.5}, rank=1, betrayer=True, pf_picking=-15, drone_score=0
    )
    assert got == ["warlord", "cannon_fodder", "friendly_fire", "traitor", "rusty"]
    got = badges(
        FRONT,
        {**POSITIVE, "saboteur": 50},
        {4: -9.0},
        {4: -9.0},
        rank=2,
        betrayer=False,
        pf_picking=40,
        drone_score=None,
    )
    assert got == ["oracle"]  # the saboteur's instrument does not make cannon fodder
