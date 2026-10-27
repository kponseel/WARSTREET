"""Feats (scored, step 5) and badges (GAME_RULES §8)."""

from __future__ import annotations

from collections.abc import Mapping

from engine import config

LONG_SLOTS = tuple(slot for slot in config.FRONT_SLOTS if slot != "saboteur")


def best_long_instruments(
    fronts: Mapping[str, Mapping[str, int]], returns: Mapping[int, float | None]
) -> set[int]:
    """Instruments with the highest weekly return among all humans' long front units."""
    candidates = {
        front[slot]
        for front in fronts.values()
        for slot in LONG_SLOTS
        if returns.get(front[slot]) is not None
    }
    if not candidates:
        return set()
    best = max(returns[i] for i in candidates)  # type: ignore[type-var]
    return {i for i in candidates if returns[i] == best}


def feats(
    front: Mapping[str, int],
    slot_pf: Mapping[str, int],
    returns: Mapping[int, float | None],
    prev_returns: Mapping[int, float | None],
    best: set[int],
) -> list[dict[str, object]]:
    """Feats of one human. `front` is the front at lock; `slot_pf` the 5 slot PF."""
    won: list[dict[str, object]] = []
    if all(slot_pf[slot] > 0 for slot in config.FRONT_SLOTS):
        won.append({"code": "total_victory", "pf": config.FEATS["total_victory"]})
    shot = sorted(front[slot] for slot in LONG_SLOTS if front[slot] in best)
    if shot:
        won.append(
            {"code": "perfect_shot", "pf": config.FEATS["perfect_shot"], "instrument_id": shot[0]}
        )
    for slot in LONG_SLOTS:
        this, prev = returns.get(front[slot]), prev_returns.get(front[slot])
        if (
            this is not None
            and prev is not None
            and prev < config.RESURRECTION_PREV_MAX_RETURN
            and this > config.RESURRECTION_THIS_MIN_RETURN
        ):
            won.append(
                {
                    "code": "resurrection",
                    "pf": config.FEATS["resurrection"],
                    "instrument_id": front[slot],
                }
            )
            break  # once per week
    for slot in LONG_SLOTS:
        this = returns.get(front[slot])
        if this is not None and this < config.HEAVY_LOSSES_MAX_RETURN:
            won.append(
                {
                    "code": "heavy_losses",
                    "pf": config.FEATS["heavy_losses"],
                    "instrument_id": front[slot],
                }
            )
    return won


def badges(
    front: Mapping[str, int],
    slot_pf: Mapping[str, int],
    returns: Mapping[int, float | None],
    prev_returns: Mapping[int, float | None],
    *,
    rank: int | None,
    betrayer: bool,
    pf_picking: int,
    drone_score: int | None,
) -> list[str]:
    codes: list[str] = []
    if rank == 1:
        codes.append("warlord")
    if slot_pf["saboteur"] >= config.ORACLE_MIN_SABOTEUR_PF:
        codes.append("oracle")
    for slot in LONG_SLOTS:
        this, prev = returns.get(front[slot]), prev_returns.get(front[slot])
        if (
            this is not None
            and prev is not None
            and prev < config.CANNON_FODDER_PREV_MAX_RETURN
            and this < config.CANNON_FODDER_THIS_MAX_RETURN
        ):
            codes.append("cannon_fodder")
            break
    if all(slot_pf[slot] < 0 for slot in config.FRONT_SLOTS):
        codes.append("friendly_fire")
    if betrayer:
        codes.append("traitor")
    if drone_score is not None and pf_picking < drone_score:
        codes.append("rusty")
    return codes
