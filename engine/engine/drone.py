"""Random valid squads: the Drone each week, and auto squads at lock (GAME_RULES §2, §9)."""

from __future__ import annotations

import hashlib
import random
from collections.abc import Mapping, Set

from engine import config
from engine.models import Instrument
from engine.squads import reserve_size, squad_errors


def seeded_rng(*parts: object) -> random.Random:
    """Deterministic RNG from e.g. (league_id, week): the same inputs give the same squad."""
    digest = hashlib.sha256(":".join(str(p) for p in parts).encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def random_squad(
    rng: random.Random,
    instruments: Mapping[int, Instrument],
    conflict_zone: Set[int],
    commander: str | None = None,
) -> dict[str, int]:
    """A random squad that satisfies every rule of GAME_RULES §3."""
    pool = sorted(instruments)
    by_region = {r: [i for i in pool if instruments[i].region == r] for r in ("EU", "US")}
    used: set[int] = set()

    def pick(candidates: list[int]) -> int:
        choice = rng.choice([c for c in candidates if c not in used])
        used.add(choice)
        return choice

    squad: dict[str, int] = {"priority_target": pick(sorted(conflict_zone & set(pool)))}
    champion_region = rng.choice(("EU", "US"))
    veteran_region = "US" if champion_region == "EU" else "EU"
    squad["champion"] = pick(by_region[champion_region])
    squad["veteran"] = pick(by_region[veteran_region])
    # The remaining two front slots fill whatever region is still short of the minimum.
    for slot in ("marksman", "saboteur"):
        counts = {
            r: sum(1 for i in squad.values() if instruments[i].region == r) for r in by_region
        }
        short = [r for r in by_region if counts[r] < config.FRONT_MIN_PER_REGION]
        region = short[0] if short else rng.choice(("EU", "US"))
        squad[slot] = pick(by_region[region])
    reserve_slots = config.RESERVE_SLOTS[: reserve_size(commander)]
    for index, slot in enumerate(reserve_slots):
        region = ("EU", "US")[index] if index < 2 else rng.choice(("EU", "US"))
        squad[slot] = pick(by_region[region])
    assert not squad_errors(squad, commander, instruments, conflict_zone)
    return squad


def drone_squad(
    league_id: str, week: str, instruments: Mapping[int, Instrument], conflict_zone: Set[int]
) -> dict[str, int]:
    return random_squad(seeded_rng("drone", league_id, week), instruments, conflict_zone)


def auto_squad(
    member_id: str,
    week: str,
    commander: str | None,
    previous: Mapping[str, int] | None,
    instruments: Mapping[int, Instrument],
    conflict_zone: Set[int],
) -> dict[str, int]:
    """Missing squad at lock: redeploy last week's squad if still valid (a stale Priority
    Target is replaced by a random Conflict Zone stock), else a random valid squad."""
    rng = seeded_rng("auto", member_id, week)
    if previous is not None:
        squad = dict(previous)
        if squad.get("priority_target") not in conflict_zone:
            free = sorted(conflict_zone - set(squad.values()))
            if free:
                squad["priority_target"] = rng.choice(free)
        if not squad_errors(squad, commander, instruments, conflict_zone):
            return squad
    return random_squad(rng, instruments, conflict_zone, commander)
