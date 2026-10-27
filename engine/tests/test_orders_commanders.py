"""Order resolution, S2 modifiers, commanders."""

from scenario import order

from engine.commanders import bastion_bonus, hunter_bonus, slot_multipliers
from engine.models import OrderResolution
from engine.orders import blockaded, is_attack, resolve_orders, s2_modifiers

NO_ALLIES: dict[str, str | None] = {}


def test_attack_kinds() -> None:
    assert [is_attack(t) for t in ("pillage", "jamming", "force_field", "intel")] == [
        True,
        True,
        False,
        False,
    ]


def test_force_field_blocks_the_first_later_attack_only() -> None:
    orders = [
        order("early", "A", "jamming", 5, target="B"),  # before the force field: not blocked
        order("ff", "B", "force_field", 10),
        order("first", "C", "blockade", 20, target="B"),  # blocked, force field consumed
        order("second", "A", "jamming", 30, target="B"),  # no shield left
        order("intel", "C", "intel", 40, target="B"),  # not an attack
    ]
    status = resolve_orders(orders, NO_ALLIES).status
    assert status == {
        "early": "applied",
        "ff": "applied",
        "first": "blocked",
        "second": "applied",
        "intel": "applied",
    }


def test_briefing_force_field_still_protects_at_resupply_and_unused_stays_pending() -> None:
    orders = [
        order("ff", "B", "force_field", 10),
        order("ff2", "B", "force_field", 11),
        order("strike", "A", "orbital_strike", 2000, target="B", slot="champion"),
    ]
    status = resolve_orders(orders, NO_ALLIES).status
    assert status == {"ff": "applied", "ff2": "pending", "strike": "blocked"}


def test_betrayal_counts_even_when_blocked_and_only_against_the_ally() -> None:
    orders = [
        order("ff", "B", "force_field", 1),
        order("a1", "A", "jamming", 2, target="B"),
        order("a2", "A", "pillage", 2000, target="B"),
        order("c1", "C", "jamming", 3, target="B"),
    ]
    result = resolve_orders(orders, {"A": "B", "B": "A", "C": None})
    assert result.betrayers == frozenset({"A"})
    assert result.status["a1"] == "blocked" and result.status["a2"] == "applied"


def test_blockade_set() -> None:
    orders = [
        order("b", "A", "blockade", 1, target="B"),
        order("c", "C", "blockade", 2, target="D"),
        order("ff", "D", "force_field", 0),
    ]
    assert blockaded(orders, resolve_orders(orders, NO_ALLIES)) == {"B"}


def _mods(member: str, orders: list) -> dict[str, object]:  # type: ignore[type-arg]
    resolution = resolve_orders(orders, NO_ALLIES)
    mods = s2_modifiers(member, slot_multipliers(None), orders, resolution)
    return {"m": mods.multipliers, "f": {s: mods.factor(s) for s in mods.multipliers}}


def test_orbital_strikes_stack_and_retreat_zeroes_a_slot() -> None:
    orders = [
        order("s1", "A", "orbital_strike", 2000, target="B", slot="veteran"),
        order("s2", "C", "orbital_strike", 2001, target="B", slot="veteran"),
        order("r", "B", "tactical_retreat", 2002, slot="champion"),
    ]
    mods = _mods("B", orders)
    assert mods["f"] == {
        "champion": 0.0,
        "veteran": 0.25,
        "marksman": 1.0,
        "saboteur": 1.0,
        "priority_target": 1.0,
    }


def test_promotion_and_reversal_apply_in_play_order() -> None:
    first = _mods(
        "A",
        [
            order("p", "A", "field_promotion", 2000, slot="marksman"),
            order("r", "A", "reversal", 2001),
        ],
    )["m"]
    assert first["champion"] == 1.0 and first["marksman"] == -1.0  # type: ignore[index]
    second = _mods(
        "A",
        [
            order("r", "A", "reversal", 2000),
            order("p", "A", "field_promotion", 2001, slot="marksman"),
        ],
    )["m"]
    assert second["champion"] == -1.0 and second["marksman"] == 2.0  # type: ignore[index]


def test_blocked_or_foreign_orders_do_not_modify() -> None:
    orders = [
        order("ff", "B", "force_field", 1),
        order("s", "A", "orbital_strike", 2000, target="B", slot="veteran"),
        order("x", "C", "reversal", 2001),
    ]
    mods = _mods("B", orders)
    assert mods["f"]["veteran"] == 1.0 and mods["m"]["marksman"] == 1.0  # type: ignore[index]
    resolution = OrderResolution(status={}, betrayers=frozenset())
    assert s2_modifiers("A", {"champion": 2.0}, [], resolution).multipliers == {"champion": 2.0}


def test_commander_multipliers() -> None:
    assert slot_multipliers("berserker")["champion"] == 3.0
    assert slot_multipliers("prophet")["saboteur"] == -2.0
    assert slot_multipliers(None) == slot_multipliers("bastion")


def test_bastion() -> None:
    assert bastion_bonus({"a": 10, "b": -3}) == 3
    assert bastion_bonus({"a": 10, "b": -150, "c": -20}) == 5
    assert bastion_bonus({"a": 0, "b": 4}) == 0


def test_hunter() -> None:
    points = {"H": 5.0, "A": 10.0, "B": 20.0, "C": 30.0, "D": 5.0}
    scores = {"H": 100, "A": 90, "B": 80, "C": 120, "D": 10}
    # A and B have more points and are outscored; C is not outscored; D has equal points.
    assert hunter_bonus("H", scores, points) == (12, ["A", "B"])
    assert hunter_bonus("H", {**scores, "B": 100}, points) == (6, ["A"])  # equal score: no
    many = {**points, "E": 40.0, "F": 50.0}
    assert hunter_bonus("H", {**scores, "E": 1, "F": 1}, many)[0] == 12  # capped
