"""Commander passives (GAME_RULES §5). Constraints on orders are enforced by the RPCs."""

from __future__ import annotations

from collections.abc import Mapping

from engine import config
from engine.rounding import round_half_away


def slot_multipliers(commander: str | None) -> dict[str, float]:
    """S1 multipliers of the 5 front slots, with the commander's replacements."""
    multipliers = dict(config.SLOT_MULTIPLIERS)
    if commander == "berserker":
        multipliers["champion"] = config.BERSERKER_CHAMPION_MULTIPLIER
    elif commander == "prophet":
        multipliers["saboteur"] = config.PROPHET_SABOTEUR_MULTIPLIER
    return multipliers


def bastion_bonus(slot_pf: Mapping[str, int]) -> int:
    """The worst slot loss (after the clamp) is reduced by up to BASTION_LOSS_REDUCTION."""
    worst = min(slot_pf.values(), default=0)
    return min(-worst, config.BASTION_LOSS_REDUCTION) if worst < 0 else 0


def hunter_bonus(
    hunter_id: str,
    scores: Mapping[str, int],
    campaign_points_before: Mapping[str, float],
) -> tuple[int, list[str]]:
    """+HUNTER_BONUS_PER_TARGET per human with strictly more campaign points (before this
    week) whom the Hunter strictly outscores this week (steps 1-8), capped."""
    mine = campaign_points_before[hunter_id]
    victims = sorted(
        member
        for member, score in scores.items()
        if member != hunter_id
        and campaign_points_before[member] > mine
        and scores[hunter_id] > score
    )
    bonus = min(len(victims) * config.HUNTER_BONUS_PER_TARGET, config.HUNTER_BONUS_MAX)
    return round_half_away(bonus), victims
