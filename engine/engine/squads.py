"""Squad validity (GAME_RULES §3), mirroring the save_squad / swap_unit RPC checks.

Returns the same error codes as the database so the jobs (auto squads, Drone) and the RPCs
agree on what a valid squad is.
"""

from __future__ import annotations

from collections.abc import Mapping, Set

from engine import config
from engine.models import Instrument


def reserve_size(commander: str | None) -> int:
    if commander == "quartermaster":
        return config.QUARTERMASTER_RESERVE_SIZE
    return config.RESERVE_SIZE


def max_swaps(commander: str | None) -> int:
    if commander == "quartermaster":
        return config.QUARTERMASTER_MAX_SWAPS
    return config.MAX_SWAPS


def front_errors(
    front: Mapping[str, int], instruments: Mapping[int, Instrument], conflict_zone: Set[int]
) -> list[str]:
    errors: list[str] = []
    for region in ("EU", "US"):
        count = sum(1 for slot in config.FRONT_SLOTS if instruments[front[slot]].region == region)
        if count < config.FRONT_MIN_PER_REGION:
            errors.append("FRONT_NEEDS_REGION")
    if instruments[front["champion"]].region == instruments[front["veteran"]].region:
        errors.append("VETERAN_SAME_REGION")
    if front["priority_target"] not in conflict_zone:
        errors.append("PRIORITY_TARGET_NOT_IN_ZONE")
    return errors


def squad_errors(
    units: Mapping[str, int],
    commander: str | None,
    instruments: Mapping[int, Instrument],
    conflict_zone: Set[int],
) -> list[str]:
    """Error codes for a full squad (front + reserve); empty when valid."""
    reserve_slots = config.RESERVE_SLOTS[: reserve_size(commander)]
    expected = set(config.FRONT_SLOTS) | set(reserve_slots)
    if set(units) - expected:
        return ["SQUAD_UNKNOWN_SLOT"]
    if expected - set(units):
        return ["SQUAD_MISSING_SLOT"]
    if any(instrument not in instruments for instrument in units.values()):
        return ["UNKNOWN_INSTRUMENT"]
    if len(set(units.values())) != len(units):
        return ["SQUAD_DUPLICATE_INSTRUMENT"]
    errors = front_errors({s: units[s] for s in config.FRONT_SLOTS}, instruments, conflict_zone)
    for region in ("EU", "US"):
        count = sum(1 for slot in reserve_slots if instruments[units[slot]].region == region)
        if count < config.RESERVE_MIN_PER_REGION:
            errors.append("RESERVE_NEEDS_REGION")
    return errors
