"""Plain data the engine computes from. No I/O: the jobs build these from the database."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Region = Literal["EU", "US"]


@dataclass(frozen=True, slots=True)
class Instrument:
    id: int
    region: Region


@dataclass(frozen=True, slots=True)
class InstrumentWeek:
    """Reference prices of one instrument for one week (GAME_RULES §2).

    Prices are raw (unadjusted). `d1`/`d2` are the dividends already assigned to S1/S2 and
    `k1`/`k2` the split ratios inside each segment (new shares per old share); a segment's
    end price and dividend are per new share. A missing price is None.
    """

    instrument_id: int
    region: Region
    p0: float | None
    p_mid: float | None
    p_end: float | None
    d1: float = 0.0
    d2: float = 0.0
    k1: float = 1.0
    k2: float = 1.0
    coef: float = 1.0
    prev_week_return: float | None = None


@dataclass(frozen=True, slots=True)
class Swap:
    slot: str
    reserve_slot: str


@dataclass(frozen=True, slots=True)
class Order:
    id: str
    member_id: str
    type: str
    created_at: datetime
    window: Literal["briefing", "resupply"]
    target_member_id: str | None = None
    target_slot: str | None = None


@dataclass(frozen=True, slots=True)
class PlayerWeek:
    member_id: str
    commander: str | None
    units: Mapping[str, int]  # slot -> instrument id, as locked (front + reserve)
    swaps: tuple[Swap, ...] = ()
    is_drone: bool = False
    campaign_points_before: float = 0.0  # Hunter compares standings before this week
    ally_member_id: str | None = None  # active pact partner this week


@dataclass(frozen=True, slots=True)
class WeekInput:
    players: tuple[PlayerWeek, ...]
    instruments: Mapping[int, InstrumentWeek]
    orders: tuple[Order, ...] = ()
    is_final: bool = False


@dataclass(frozen=True, slots=True)
class PlayerResult:
    member_id: str
    is_drone: bool
    pf_total: int
    pf_picking: int
    rank: int | None
    campaign_points: float
    badges: tuple[str, ...]
    breakdown: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OrderResolution:
    status: dict[str, str]  # order id -> applied | blocked | pending (unused force field)
    betrayers: frozenset[str]


@dataclass(frozen=True, slots=True)
class WeekResult:
    players: dict[str, PlayerResult]
    orders: OrderResolution
