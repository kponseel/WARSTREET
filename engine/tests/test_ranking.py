"""Ranks, campaign points, standings, Bounty, ammo and order costs."""

import pytest

from engine.ranking import (
    WeekRecord,
    ammo_delta,
    bounty_member,
    campaign_standings,
    competition_ranks,
    order_cost,
    weekly_campaign_points,
)


def test_competition_ranks() -> None:
    assert competition_ranks({"a": 10, "b": 8, "c": 8, "d": 5}) == {"a": 1, "b": 2, "c": 2, "d": 4}


@pytest.mark.parametrize(
    ("scores", "expected"),
    [
        ({"a": 3, "b": 2, "c": 1}, {"a": 10, "b": 5, "c": 2}),
        ({"a": 4, "b": 3, "c": 2, "d": 1}, {"a": 10, "b": 6, "c": 3, "d": 1}),
        ({"a": 5, "b": 4, "c": 3, "d": 2, "e": 1}, {"a": 10, "b": 7, "c": 5, "d": 3, "e": 1}),
        ({"a": 9, "b": 5, "c": 5, "d": 1}, {"a": 10, "b": 4.5, "c": 4.5, "d": 1}),  # rules example
        ({"a": 5, "b": 5, "c": 5}, {"a": 17 / 3, "b": 17 / 3, "c": 17 / 3}),
    ],
)
def test_weekly_campaign_points(scores: dict[str, int], expected: dict[str, float]) -> None:
    assert weekly_campaign_points(scores, is_final=False) == pytest.approx(expected)


def test_final_week_doubles_points() -> None:
    assert weekly_campaign_points({"a": 2, "b": 1, "c": 0}, is_final=True) == {
        "a": 20,
        "b": 10,
        "c": 4,
    }


def test_campaign_standings_tiebreaks() -> None:
    history = [
        WeekRecord("a", 10, 1, 100),
        WeekRecord("b", 5, 2, 90),
        WeekRecord("c", 2, 3, 50),
        WeekRecord("a", 2, 3, 10),
        WeekRecord("b", 5, 2, 80),
        WeekRecord("c", 10, 1, 200),
    ]
    standings = campaign_standings(["a", "b", "c"], history)
    # 12 points each for a and c (1 win each), c has more PF; b has 10 points.
    assert [(s.member_id, s.rank) for s in standings] == [("c", 1), ("a", 2), ("b", 3)]
    tied = campaign_standings(["x", "y"], [WeekRecord("x", 5, 1, 10), WeekRecord("y", 5, 1, 10)])
    assert [s.rank for s in tied] == [1, 1]


def test_bounty() -> None:
    assert bounty_member({"a": 10, "b": 5}) == "a"
    assert bounty_member({"a": 10, "b": 10}) is None
    assert bounty_member({"a": 0, "b": 0, "c": 0}) is None
    assert bounty_member({}) is None


@pytest.mark.parametrize(
    ("commander", "balance", "week", "rank", "humans", "expected"),
    [
        ("bastion", 0, 1, 3, 3, 3),  # week 1: income only
        ("technomancer", 0, 1, 1, 3, 4),
        ("bastion", 0, 2, 3, 3, 4),  # rank 3 > ceil(3/2) = 2: catch-up
        ("bastion", 0, 2, 2, 3, 3),  # rank 2 is not strictly in the bottom half
        ("bastion", 0, 2, 3, 4, 4),  # rank 3 > ceil(4/2) = 2: catch-up
        ("bastion", 0, 2, 2, 4, 3),  # rank 2 = ceil(4/2): no catch-up
        ("bastion", 3, 2, 1, 3, 2),  # capped at 5
        ("technomancer", 4, 2, 1, 3, 2),  # Technomancer cap 6
        ("bastion", 5, 2, 3, 3, 0),  # already at the cap
    ],
)
def test_ammo_delta(
    commander: str, balance: int, week: int, rank: int, humans: int, expected: int
) -> None:
    assert (
        ammo_delta(commander, balance, week_number=week, campaign_rank=rank, humans=humans)
        == expected
    )


def test_ammo_never_lowers_a_balance() -> None:
    assert ammo_delta("bastion", 7, week_number=3, campaign_rank=1, humans=3) == 0


def test_order_cost() -> None:
    assert order_cost("pillage", False) == 3
    assert order_cost("pillage", True) == 2
    assert order_cost("jamming", True) == 1  # minimum 1
    assert order_cost("force_field", True) == 1  # not an attack: no discount
