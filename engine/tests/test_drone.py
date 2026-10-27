"""Random squads: the Drone and auto squads."""

from engine.drone import auto_squad, drone_squad, random_squad, seeded_rng
from engine.models import Instrument
from engine.squads import squad_errors

INSTRUMENTS = {i: Instrument(i, "EU" if i <= 50 else "US") for i in range(1, 101)}
ZONE = {3, 17, 52, 60, 71, 88, 90, 99}


def test_drone_squads_are_valid_and_deterministic() -> None:
    for week in range(60):
        squad = drone_squad("league", f"2026-W{week}", INSTRUMENTS, ZONE)
        assert squad_errors(squad, None, INSTRUMENTS, ZONE) == []
    assert drone_squad("l", "w", INSTRUMENTS, ZONE) == drone_squad("l", "w", INSTRUMENTS, ZONE)
    assert drone_squad("l", "w1", INSTRUMENTS, ZONE) != drone_squad("l", "w2", INSTRUMENTS, ZONE)


def test_quartermaster_random_squad_has_three_reserves() -> None:
    for seed in range(30):
        squad = random_squad(seeded_rng(seed), INSTRUMENTS, ZONE, "quartermaster")
        assert "reserve_3" in squad and not squad_errors(squad, "quartermaster", INSTRUMENTS, ZONE)


VALID = {
    "champion": 51,
    "veteran": 1,
    "marksman": 53,
    "saboteur": 2,
    "priority_target": 52,
    "reserve_1": 4,
    "reserve_2": 54,
}


def test_auto_squad_redeploys_last_week() -> None:
    assert auto_squad("m", "w", "bastion", VALID, INSTRUMENTS, ZONE) == VALID


def test_auto_squad_replaces_a_stale_priority_target() -> None:
    zone = {60, 71}
    squad = auto_squad("m", "w", "bastion", VALID, INSTRUMENTS, zone)
    assert squad["priority_target"] in zone
    assert {k: v for k, v in squad.items() if k != "priority_target"} == {
        k: v for k, v in VALID.items() if k != "priority_target"
    }


def test_auto_squad_falls_back_to_random() -> None:
    invalid = {**VALID, "reserve_2": 5}  # two EU reserves
    squad = auto_squad("m", "w", "bastion", invalid, INSTRUMENTS, ZONE)
    assert squad != invalid and not squad_errors(squad, "bastion", INSTRUMENTS, ZONE)
    first_week = auto_squad("m", "w", "quartermaster", None, INSTRUMENTS, ZONE)
    assert not squad_errors(first_week, "quartermaster", INSTRUMENTS, ZONE)
