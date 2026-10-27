"""Test helpers: instruments built from chosen segment returns, players, orders."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from engine.models import InstrumentWeek, Order, PlayerWeek, Region, Swap

T0 = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)

# id -> (region, r1 %, r2 %, coef, previous-week return %)
RETURNS: dict[int, tuple[Region, float, float, float, float | None]] = {
    1: ("EU", 2, 1, 1.0, None),
    2: ("EU", -1, -2, 1.0, None),
    3: ("EU", 3, 0, 0.5, None),
    4: ("EU", 0, 4, 1.0, None),
    5: ("EU", 1, 1, 1.0, None),
    6: ("EU", -8, -5, 1.0, -7.0),
    7: ("EU", 4, 3, 1.0, -8.0),
    11: ("US", 4, -1, 1.0, None),
    12: ("US", -3, 2, 1.0, None),
    13: ("US", 5, 5, 1.0, None),
    14: ("US", 1, 3, 1.0, None),
    15: ("US", -2, -2, 1.0, None),
    16: ("US", 2, 2, 1.0, None),
    17: ("US", -6, -6, 1.0, None),
    18: ("US", 1, -1, 1.0, None),
    19: ("US", 0, 0, 1.0, None),
    20: ("US", 6, 4, 1.0, None),
}


def instrument_week(instrument_id: int) -> InstrumentWeek:
    region, r1, r2, coef, prev = RETURNS[instrument_id]
    p_mid = 100 * (1 + r1 / 100)
    return InstrumentWeek(
        instrument_id=instrument_id,
        region=region,
        p0=100.0,
        p_mid=p_mid,
        p_end=p_mid * (1 + r2 / 100),
        coef=coef,
        prev_week_return=prev,
    )


def instruments() -> dict[int, InstrumentWeek]:
    return {i: instrument_week(i) for i in RETURNS}


SLOTS = ("champion", "veteran", "marksman", "saboteur", "priority_target")


def player(
    member: str,
    commander: str | None,
    front: tuple[int, int, int, int, int],
    reserve: tuple[int, ...],
    *,
    swaps: tuple[tuple[str, str], ...] = (),
    points: float = 0.0,
    ally: str | None = None,
    drone: bool = False,
) -> PlayerWeek:
    units = dict(zip(SLOTS, front, strict=True))
    units.update({f"reserve_{i + 1}": inst for i, inst in enumerate(reserve)})
    return PlayerWeek(
        member_id=member,
        commander=commander,
        units=units,
        swaps=tuple(Swap(slot, reserve_slot) for slot, reserve_slot in swaps),
        is_drone=drone,
        campaign_points_before=points,
        ally_member_id=ally,
    )


def order(
    order_id: str,
    member: str,
    order_type: str,
    minute: int,
    target: str | None = None,
    slot: str | None = None,
) -> Order:
    window = "briefing" if order_type in ("blockade", "intel") or minute < 1000 else "resupply"
    return Order(
        id=order_id,
        member_id=member,
        type=order_type,
        created_at=T0 + timedelta(minutes=minute),
        window=window,
        target_member_id=target,
        target_slot=slot,
    )
