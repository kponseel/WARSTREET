"""Order resolution (GAME_RULES §6-7).

Orders resolve when their window closes, in play-timestamp order. Resolving every order
played so far is the same at lock and at resupply close: later orders never change the
status of earlier ones, so the jobs can call `resolve_orders` at each window close.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from engine import config
from engine.models import Order, OrderResolution


def is_attack(order_type: str) -> bool:
    return config.ORDERS[order_type]["kind"] == "attack"


def _ordered(orders: Iterable[Order]) -> list[Order]:
    return sorted(orders, key=lambda o: (o.created_at, o.id))


def resolve_orders(orders: Iterable[Order], allies: Mapping[str, str | None]) -> OrderResolution:
    """Statuses of all orders and the set of betrayers.

    - A force field protects its owner from the first attack played against them after the
      force field's own play time; several force fields each block one attack, in order.
      A triggered force field is `applied`; an unused one stays `pending`.
    - A blocked attack is `blocked`; every other order is `applied`.
    - Betrayal: any attack against one's active pact partner, blocked or not.
    """
    status: dict[str, str] = {}
    shields: dict[str, list[Order]] = {}
    betrayers: set[str] = set()
    for order in _ordered(orders):
        if order.type == "force_field":
            shields.setdefault(order.member_id, []).append(order)
            status[order.id] = "pending"
            continue
        if not is_attack(order.type):
            status[order.id] = "applied"
            continue
        target = order.target_member_id
        if target is not None and allies.get(order.member_id) == target:
            betrayers.add(order.member_id)
        queue = shields.get(target or "", [])
        if queue:
            shield = queue.pop(0)
            status[shield.id] = "applied"
            status[order.id] = "blocked"
        else:
            status[order.id] = "applied"
    return OrderResolution(status=status, betrayers=frozenset(betrayers))


def blockaded(orders: Iterable[Order], resolution: OrderResolution) -> set[str]:
    """Members hit by an applied Blockade."""
    return {
        o.target_member_id
        for o in orders
        if o.type == "blockade" and o.target_member_id and resolution.status.get(o.id) == "applied"
    }


@dataclass(slots=True)
class SlotModifiers:
    """S2 effects on one player's front slots."""

    multipliers: dict[str, float]  # effective S2 multiplier per front slot
    factors: dict[str, float] = field(default_factory=dict)  # orbital strike / retreat
    notes: dict[str, list[str]] = field(default_factory=dict)  # order codes per slot

    def factor(self, slot: str) -> float:
        return self.factors.get(slot, 1.0)

    def note(self, slot: str, code: str) -> None:
        self.notes.setdefault(slot, []).append(code)


def s2_modifiers(
    member_id: str,
    s1_multipliers: Mapping[str, float],
    orders: Iterable[Order],
    resolution: OrderResolution,
) -> SlotModifiers:
    """Applies the applied S2 orders affecting one player's slots, in play order.

    Effects follow the slot, not the unit (a swapped-in unit inherits them).
    """
    mods = SlotModifiers(multipliers=dict(s1_multipliers))
    for order in _ordered(orders):
        if resolution.status.get(order.id) != "applied":
            continue
        if order.type == "orbital_strike" and order.target_member_id == member_id:
            slot = order.target_slot or ""
            mods.factors[slot] = mods.factor(slot) * config.ORBITAL_STRIKE_FACTOR
            mods.note(slot, "orbital_strike")
        elif order.member_id != member_id:
            continue
        elif order.type == "tactical_retreat" and order.target_slot:
            mods.factors[order.target_slot] = 0.0
            mods.note(order.target_slot, "tactical_retreat")
        elif order.type == "field_promotion" and order.target_slot:
            m = mods.multipliers
            m["champion"], m[order.target_slot] = m[order.target_slot], m["champion"]
            mods.note("champion", "field_promotion")
            mods.note(order.target_slot, "field_promotion")
        elif order.type == "reversal":
            mods.multipliers["marksman"] = config.REVERSAL_MARKSMAN_MULTIPLIER
            mods.note("marksman", "reversal")
    return mods
