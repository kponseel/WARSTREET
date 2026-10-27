"""Ranks, campaign points, standings, Bounty and ammo (GAME_RULES §4, §6)."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from engine import config


def competition_ranks(scores: Mapping[str, float]) -> dict[str, int]:
    """1-based ranks, ties share the best rank (10, 8, 8, 5 -> 1, 2, 2, 4)."""
    ordered = sorted(scores.values(), reverse=True)
    return {member: ordered.index(score) + 1 for member, score in scores.items()}


def weekly_campaign_points(scores: Mapping[str, int], is_final: bool) -> dict[str, float]:
    """Points by weekly rank among humans; tied players share the average of their places."""
    table = config.CAMPAIGN_POINTS[len(scores)]
    ranks = competition_ranks(scores)
    multiplier = config.FINAL_WEEK_MULTIPLIER if is_final else 1
    points: dict[str, float] = {}
    for member, rank in ranks.items():
        tied = sum(1 for r in ranks.values() if r == rank)
        share = sum(table[rank - 1 : rank - 1 + tied]) / tied
        points[member] = share * multiplier
    return points


@dataclass(frozen=True, slots=True)
class WeekRecord:
    member_id: str
    campaign_points: float
    rank: int
    pf_total: int


@dataclass(frozen=True, slots=True)
class Standing:
    member_id: str
    campaign_points: float
    weekly_wins: int
    pf_cumulative: int
    rank: int


def campaign_standings(members: Sequence[str], history: Sequence[WeekRecord]) -> list[Standing]:
    """Points, then most weekly wins, then cumulative PF; full ties share a rank."""
    totals = {m: [0.0, 0, 0] for m in members}
    for record in history:
        entry = totals[record.member_id]
        entry[0] += record.campaign_points
        entry[1] += 1 if record.rank == 1 else 0
        entry[2] += record.pf_total
    keys = {m: (t[0], t[1], t[2]) for m, t in totals.items()}
    ordered = sorted(keys.values(), reverse=True)
    standings = [
        Standing(m, float(t[0]), int(t[1]), int(t[2]), ordered.index(keys[m]) + 1)
        for m, t in totals.items()
    ]
    return sorted(standings, key=lambda s: (s.rank, s.member_id))


def bounty_member(points_before: Mapping[str, float]) -> str | None:
    """The strict campaign leader (no tie) before this week, or None."""
    if not points_before:
        return None
    best = max(points_before.values())
    leaders = [m for m, p in points_before.items() if p == best]
    return leaders[0] if len(leaders) == 1 else None


def ammo_delta(
    commander: str | None,
    balance: int,
    *,
    week_number: int,
    campaign_rank: int,
    humans: int,
) -> int:
    """Ammo credited at briefing opening: income, catch-up (week ≥ 2, strictly bottom
    half), capped after both; the cap never lowers a balance."""
    techno = commander == "technomancer"
    income = config.AMMO_INCOME + (config.TECHNOMANCER_EXTRA_INCOME if techno else 0)
    if week_number >= 2 and campaign_rank > math.ceil(humans / 2):
        income += config.CATCH_UP_AMMO
    cap = config.TECHNOMANCER_AMMO_CAP if techno else config.AMMO_CAP
    return max(0, min(balance + income, cap) - balance)


def order_cost(order_type: str, target_has_bounty: bool) -> int:
    spec = config.ORDERS[order_type]
    cost = int(spec["cost"])  # type: ignore[call-overload]
    if target_has_bounty and spec["kind"] == "attack":
        cost = max(config.MIN_ORDER_COST, cost - config.BOUNTY_DISCOUNT)
    return cost
