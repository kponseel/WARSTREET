"""Rounding, returns, squad validity, coefficients, Conflict Zone, weather."""

import pytest

from engine import config
from engine.conflict_zone import ZoneCandidate, coefficient, conflict_zone, display_class, vol12w
from engine.models import Instrument, InstrumentWeek
from engine.returns import s1_return, s2_return, segment_return, weekly_return
from engine.rounding import clamp, round_half_away
from engine.squads import max_swaps, reserve_size, squad_errors
from engine.weather import weather_flags


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (2.5, 3),
        (-2.5, -3),
        (2.4999, 2),
        (-0.5, -1),
        (0.5, 1),
        (0.0, 0),
        (64.2, 64),
        (-178.75, -179),
    ],
)
def test_round_half_away(value: float, expected: int) -> None:
    assert round_half_away(value) == expected


def test_clamp() -> None:
    assert clamp(200, -150, 150) == 150 and clamp(-200, -150, 150) == -150 and clamp(3, 0, 5) == 3


def test_segment_returns_with_dividend_and_split() -> None:
    assert segment_return(100, 103) == pytest.approx(3.0)
    assert segment_return(100, 98, dividend=2) == pytest.approx(0.0)  # ex-dividend drop
    assert segment_return(100, 51, split=2) == pytest.approx(2.0)  # 2-for-1 split
    assert segment_return(None, 100) is None and segment_return(100, None) is None
    assert segment_return(0, 100) is None


def test_week_returns_and_missing_data() -> None:
    week = InstrumentWeek(1, "EU", p0=100, p_mid=49, p_end=50, d1=1, d2=0.5, k1=2, k2=1)
    assert s1_return(week) == pytest.approx(0.0)  # (49 + 1) * 2 / 100
    assert s2_return(week) == pytest.approx((50.5 / 49 - 1) * 100)
    # ((50 + 0.5) * 1 * 2 + 1 * 2) / 100 - 1
    assert weekly_return(week) == pytest.approx(3.0)
    halted = InstrumentWeek(2, "US", p0=100, p_mid=None, p_end=None)
    assert s1_return(halted) is None and s2_return(halted) is None and weekly_return(halted) is None
    assert weekly_return(InstrumentWeek(3, "US", p0=None, p_mid=1, p_end=1)) is None


REGIONS = {i: Instrument(i, "EU" if i <= 10 else "US") for i in range(1, 21)}
ZONE = {13, 16, 4}
VALID = {
    "champion": 11,
    "veteran": 1,
    "marksman": 12,
    "saboteur": 2,
    "priority_target": 13,
    "reserve_1": 3,
    "reserve_2": 14,
}


@pytest.mark.parametrize(
    ("change", "commander", "errors"),
    [
        ({}, None, []),
        ({"reserve_3": 15}, None, ["SQUAD_UNKNOWN_SLOT"]),
        ({}, "quartermaster", ["SQUAD_MISSING_SLOT"]),
        ({"reserve_3": 15}, "quartermaster", []),
        ({"reserve_2": 99}, None, ["UNKNOWN_INSTRUMENT"]),
        ({"reserve_2": 11}, None, ["SQUAD_DUPLICATE_INSTRUMENT"]),
        ({"veteran": 15, "saboteur": 16}, None, ["FRONT_NEEDS_REGION", "VETERAN_SAME_REGION"]),
        ({"priority_target": 14, "reserve_2": 13}, None, ["PRIORITY_TARGET_NOT_IN_ZONE"]),
        ({"reserve_1": 15}, None, ["RESERVE_NEEDS_REGION"]),
    ],
)
def test_squad_errors(change: dict[str, int], commander: str | None, errors: list[str]) -> None:
    assert squad_errors({**VALID, **change}, commander, REGIONS, ZONE) == errors


def test_squad_missing_slot() -> None:
    squad = {k: v for k, v in VALID.items() if k != "champion"}
    assert squad_errors(squad, None, REGIONS, ZONE) == ["SQUAD_MISSING_SLOT"]


def test_quartermaster_sizes() -> None:
    assert (reserve_size(None), reserve_size("quartermaster")) == (2, 3)
    assert (max_swaps("bastion"), max_swaps("quartermaster")) == (1, 2)


def test_vol_and_coefficient() -> None:
    assert vol12w([1.0]) is None
    assert vol12w([1.0, 3.0]) == pytest.approx(1.4142135, rel=1e-6)  # sample stdev
    assert vol12w([100.0] * 5 + [1.0, 3.0] * 6) == pytest.approx(vol12w([1.0, 3.0] * 6))
    assert coefficient(None) == 1.0
    assert coefficient(0.0) == config.COEF_MAX
    assert coefficient(3.5) == pytest.approx(1.0)
    assert coefficient(1.0) == config.COEF_MAX  # 3.5 clamped to 2
    assert coefficient(100.0) == config.COEF_MIN


@pytest.mark.parametrize(
    ("vol", "expected"),
    [
        (None, None),
        (2.9, "armored"),
        (3.0, "infantry"),
        (4.99, "infantry"),
        (5.0, "commando"),
        (8.9, "commando"),
        (9.0, "kamikaze"),
    ],
)
def test_display_class(vol: float | None, expected: str | None) -> None:
    assert display_class(vol) == expected


def test_conflict_zone_ordering() -> None:
    candidates = [ZoneCandidate(i, False, None, float(i % 7) - 3) for i in range(1, 21)]
    candidates[4] = ZoneCandidate(5, True, 10.0, 0.0)
    candidates[9] = ZoneCandidate(10, True, 50.0, 0.0)
    candidates[14] = ZoneCandidate(15, True, None, 9.0)
    zone = conflict_zone(candidates)
    assert len(zone) == config.CONFLICT_ZONE_SIZE
    assert zone[:3] == [10, 5, 15]  # earnings first, largest market cap first
    moves = {c.instrument_id: abs(c.last_week_return or 0) for c in candidates}
    assert [moves[i] for i in zone[3:]] == sorted((moves[i] for i in zone[3:]), reverse=True)


def test_weather() -> None:
    assert weather_flags(5.0, True, 4.0) == ["on_fire", "earnings", "roller_coaster"]
    assert weather_flags(-5.0, False, 3.9) == ["frozen"]
    assert weather_flags(None, False, None) == []
    assert weather_flags(4.99, False, None) == []
