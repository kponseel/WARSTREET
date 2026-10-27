"""Weekly scoring in the exact order of GAME_RULES §4, with a breakdown of every PF.

Steps: 1 unit segment PF (with commander multipliers and S2 order effects), 2 swaps,
3 unit weekly PF (rounded, clamped per slot), 4 Elite unit, 5 feats, 6 Bastion,
7 Pillage, 8 Betrayal, 9 Hunter, 10 total. The Drone is scored with steps 1-3 only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from engine import config
from engine.commanders import bastion_bonus, hunter_bonus, slot_multipliers
from engine.feats import badges, best_long_instruments, feats
from engine.models import InstrumentWeek, PlayerResult, PlayerWeek, WeekInput, WeekResult
from engine.orders import SlotModifiers, blockaded, resolve_orders, s2_modifiers
from engine.ranking import competition_ranks, weekly_campaign_points
from engine.returns import s1_return, s2_return, weekly_return
from engine.rounding import clamp, round_half_away


def _r(value: float | None) -> float | None:
    """Rounds floats for the stored breakdown (display only, never used in maths)."""
    return None if value is None else round(value, 4)


@dataclass(slots=True)
class _SlotScore:
    pf: int
    pf_s2: float  # S2 PF after order effects, before rounding and clamp (Pillage base)
    detail: dict[str, object]


def _segment(
    instrument: InstrumentWeek | None,
    ret: float | None,
    multiplier: float,
    factor: float,
) -> tuple[float, dict[str, object]]:
    coef = instrument.coef if instrument else 0.0
    missing = ret is None
    pf = (ret or 0.0) * config.PF_PER_PERCENT * multiplier * coef * factor
    return pf, {
        "instrument_id": instrument.instrument_id if instrument else None,
        "return": _r(ret),
        "multiplier": multiplier,
        "coef": _r(coef),
        "modifier": factor,
        "pf": _r(pf),
        "missing": missing,
    }


def _score_slot(
    slot: str,
    player: PlayerWeek,
    instruments: Mapping[int, InstrumentWeek],
    s1_multiplier: float,
    mods: SlotModifiers,
    swaps: Mapping[str, str],
) -> _SlotScore:
    unit_s1 = instruments.get(player.units[slot])
    reserve_slot = swaps.get(slot)
    unit_s2 = instruments.get(player.units[reserve_slot]) if reserve_slot else unit_s1
    pf1, s1 = _segment(unit_s1, s1_return(unit_s1) if unit_s1 else None, s1_multiplier, 1.0)
    pf2, s2 = _segment(
        unit_s2,
        s2_return(unit_s2) if unit_s2 else None,
        mods.multipliers[slot],
        mods.factor(slot),
    )
    raw = pf1 + pf2
    rounded = round_half_away(raw)
    pf = int(clamp(rounded, -config.UNIT_PF_CLAMP, config.UNIT_PF_CLAMP))
    return _SlotScore(
        pf=pf,
        pf_s2=pf2,
        detail={
            "s1": s1,
            "s2": s2,
            "swapped_from": reserve_slot,
            "orders": mods.notes.get(slot, []),
            "raw": _r(raw),
            "pf": pf,
            "clamped": pf != rounded,
        },
    )


def score_week(week: WeekInput) -> WeekResult:
    allies = {p.member_id: p.ally_member_id for p in week.players}
    resolution = resolve_orders(week.orders, allies)
    blocked = blockaded(week.orders, resolution)
    humans = [p for p in week.players if not p.is_drone]
    drone = next((p for p in week.players if p.is_drone), None)

    returns = {i: weekly_return(w) for i, w in week.instruments.items()}
    prev_returns = {i: w.prev_week_return for i, w in week.instruments.items()}
    fronts = {p.member_id: {s: p.units[s] for s in config.FRONT_SLOTS} for p in week.players}

    # Steps 1-3.
    slots: dict[str, dict[str, _SlotScore]] = {}
    for player in week.players:
        multipliers = slot_multipliers(None if player.is_drone else player.commander)
        if player.is_drone:
            mods = SlotModifiers(multipliers=dict(multipliers))
        else:
            mods = s2_modifiers(player.member_id, multipliers, week.orders, resolution)
        swaps = (
            {} if player.member_id in blocked else {s.slot: s.reserve_slot for s in player.swaps}
        )
        slots[player.member_id] = {
            slot: _score_slot(slot, player, week.instruments, multipliers[slot], mods, swaps)
            for slot in config.FRONT_SLOTS
        }
    slot_pf = {m: {s: v.pf for s, v in per.items()} for m, per in slots.items()}
    picking = {m: sum(per.values()) for m, per in slot_pf.items()}

    # Step 4: Elite unit (front at lock, unique among humans).
    holders: dict[int, int] = {}
    for player in humans:
        for instrument in set(fronts[player.member_id].values()):
            holders[instrument] = holders.get(instrument, 0) + 1
    elite = {
        p.member_id: sorted(i for i in fronts[p.member_id].values() if holders[i] == 1)
        for p in humans
    }

    # Step 5: feats.
    best = best_long_instruments({p.member_id: fronts[p.member_id] for p in humans}, returns)
    won = {
        p.member_id: feats(fronts[p.member_id], slot_pf[p.member_id], returns, prev_returns, best)
        for p in humans
    }

    # Steps 6-8.
    bastion = {
        p.member_id: bastion_bonus(slot_pf[p.member_id]) if p.commander == "bastion" else 0
        for p in humans
    }
    pillage: dict[str, list[dict[str, object]]] = {p.member_id: [] for p in humans}
    for order in week.orders:
        target = order.target_member_id
        if order.type != "pillage" or resolution.status.get(order.id) != "applied":
            continue
        if target not in slots or order.member_id not in pillage or target not in pillage:
            continue
        base = sum(v.pf_s2 for v in slots[target].values())
        amount = round_half_away(base * config.PILLAGE_SHARE) if base > 0 else 0
        line = {"order_id": order.id, "from": target, "to": order.member_id, "base": _r(base)}
        pillage[order.member_id].append({**line, "pf": amount})
        pillage[target].append({**line, "pf": -amount})
    betrayal = {
        p.member_id: config.BETRAYAL_PENALTY if p.member_id in resolution.betrayers else 0
        for p in humans
    }

    def through_step_8(member: str) -> int:
        return (
            picking[member]
            + len(elite[member]) * config.ELITE_UNIT_BONUS
            + sum(int(f["pf"]) for f in won[member])  # type: ignore[call-overload]
            + bastion[member]
            + sum(int(line["pf"]) for line in pillage[member])  # type: ignore[call-overload]
            + betrayal[member]
        )

    scores_1_8 = {p.member_id: through_step_8(p.member_id) for p in humans}

    # Step 9: Hunter.
    points_before = {p.member_id: p.campaign_points_before for p in humans}
    hunter: dict[str, tuple[int, list[str]]] = {
        p.member_id: (
            hunter_bonus(p.member_id, scores_1_8, points_before)
            if p.commander == "hunter"
            else (0, [])
        )
        for p in humans
    }

    # Step 10, ranks, campaign points, badges.
    totals = {m: scores_1_8[m] + hunter[m][0] for m in scores_1_8}
    ranks = competition_ranks(totals)
    points = weekly_campaign_points(totals, week.is_final) if totals else {}
    drone_score = picking[drone.member_id] if drone else None

    results: dict[str, PlayerResult] = {}
    for player in week.players:
        member = player.member_id
        breakdown: dict[str, object] = {
            "slots": {s: v.detail for s, v in slots[member].items()},
            "pf_picking": picking[member],
        }
        if player.is_drone:
            breakdown["pf_total"] = picking[member]
            results[member] = PlayerResult(
                member_id=member,
                is_drone=True,
                pf_total=picking[member],
                pf_picking=picking[member],
                rank=None,
                campaign_points=0.0,
                badges=(),
                breakdown=breakdown,
            )
            continue
        breakdown.update(
            {
                "elite": {
                    "instruments": elite[member],
                    "pf": len(elite[member]) * config.ELITE_UNIT_BONUS,
                },
                "feats": won[member],
                "bastion": bastion[member],
                "pillage": pillage[member],
                "betrayal": betrayal[member],
                "hunter": {"pf": hunter[member][0], "victims": hunter[member][1]},
                "pf_total": totals[member],
            }
        )
        results[member] = PlayerResult(
            member_id=member,
            is_drone=False,
            pf_total=totals[member],
            pf_picking=picking[member],
            rank=ranks[member],
            campaign_points=points[member],
            badges=tuple(
                badges(
                    fronts[member],
                    slot_pf[member],
                    returns,
                    prev_returns,
                    rank=ranks[member],
                    betrayer=member in resolution.betrayers,
                    pf_picking=picking[member],
                    drone_score=drone_score,
                )
            ),
            breakdown=breakdown,
        )
    return WeekResult(players=results, orders=resolution)
