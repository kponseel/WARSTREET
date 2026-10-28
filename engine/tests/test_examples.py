"""The tutorial's worked examples (engine/examples.py) agree with the rules in config.py."""

from engine import config
from engine.examples import build_examples


def per_percent(slot: str) -> float:
    return config.PF_PER_PERCENT * config.SLOT_MULTIPLIERS[slot]


def test_week_slots_follow_the_slot_multipliers():
    examples = build_examples()
    week = examples["week"]
    assert [unit["slot"] for unit in week] == list(config.FRONT_SLOTS)
    for unit in week:
        assert unit["pf"] == round(unit["move"] * per_percent(unit["slot"]))
    assert examples["weekUnitsTotal"] == sum(unit["pf"] for unit in week)


def test_commander_examples_change_only_what_the_commander_changes():
    ex = build_examples()
    # Bastion: the worst slot loses up to BASTION_LOSS_REDUCTION less.
    assert ex["bastionBefore"] < 0
    assert ex["bastionAfter"] - ex["bastionBefore"] == min(
        config.BASTION_LOSS_REDUCTION, -ex["bastionBefore"]
    )
    # Berserker: the Champion multiplier, both ways.
    ratio = config.BERSERKER_CHAMPION_MULTIPLIER / config.SLOT_MULTIPLIERS["champion"]
    assert ex["berserkerAfter"] == round(ex["berserkerBefore"] * ratio)
    assert ex["berserkerDownAfter"] == round(ex["berserkerDownBefore"] * ratio)
    assert ex["berserkerDownBefore"] == -ex["berserkerBefore"]
    # Doom Prophet: the Saboteur multiplier, both ways.
    ratio = config.PROPHET_SABOTEUR_MULTIPLIER / config.SLOT_MULTIPLIERS["saboteur"]
    assert ex["prophetBefore"] > 0 > ex["prophetUpBefore"]
    assert ex["prophetAfter"] == round(ex["prophetBefore"] * ratio)
    assert ex["prophetUpAfter"] == round(ex["prophetUpBefore"] * ratio)
    # Hunter: per player ahead that you beat, capped.
    assert ex["hunterOne"] == config.HUNTER_BONUS_PER_TARGET
    assert ex["hunterBoth"] == min(2 * config.HUNTER_BONUS_PER_TARGET, config.HUNTER_BONUS_MAX)


def test_thursday_swaps_help_the_swapped_slot():
    ex = build_examples()
    assert ex["swapAfter"] > ex["swapBefore"]
    assert ex["qmAfter"] > ex["qmBefore"]
    assert ex["swapOut"] != ex["swapIn"] and ex["qmSwapOut"] != ex["qmSwapIn"]


def test_examples_are_flat_numbers_and_names():
    for key, value in build_examples().items():
        if key == "week":
            continue
        assert isinstance(value, int | float | str), key
