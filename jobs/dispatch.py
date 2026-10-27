"""Front Dispatch, the league gazette (GAME_RULES §10).

Each edition is stored as an `events` row of kind `dispatch`: a template key, variables
and a variant index. The English and French texts live in web/src/i18n (`<key>.<variant>`),
so each player reads it in their own language; the variant index is the same in both
languages and is picked deterministically from (league, week, edition).

Before the debrief a Dispatch never names a Shadow or a jammed player as leader, never
mentions a Shadow's units or swap, and never gives a jammed player's score or rank.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from engine.drone import seeded_rng

VARIANTS = 3
I18N_DIR = Path(__file__).resolve().parents[1] / "web" / "src" / "i18n"

Vars = dict[str, str | int | float]


@dataclass(frozen=True, slots=True)
class Dispatch:
    template_key: str
    vars: Vars
    variant: int


def pick_variant(league_id: str, week: str, edition: str) -> int:
    return seeded_rng("dispatch", league_id, week, edition).randrange(VARIANTS)


@dataclass(frozen=True, slots=True)
class LivePlayer:
    pseudo: str
    pf: float | None  # None when hidden
    hidden: bool  # Shadow or jammed: never named before the debrief


def monday(
    league_id: str, week: str, players: Sequence[LivePlayer], mover: str | None, move: float | None
) -> Dispatch:
    """Opening edition: biggest early mover and first live leader (visible players only)."""
    visible = [p for p in players if not p.hidden and p.pf is not None]
    variant = pick_variant(league_id, week, "monday")
    base: Vars = {"mover": mover or "-", "move": round(move or 0.0, 1)}
    if not visible:
        return Dispatch("dispatch.monday_fog", base, variant)
    leader = max(visible, key=lambda p: (p.pf, p.pseudo))
    return Dispatch(
        "dispatch.monday", {**base, "leader": leader.pseudo, "pf": round(leader.pf or 0.0)}, variant
    )


def thursday(
    league_id: str, week: str, *, swaps: int, attacks: int, blocked: int, pacts: int
) -> Dispatch:
    """Resupply recap. Counts only: a Shadow's swap is not counted, attackers stay unnamed."""
    return Dispatch(
        "dispatch.thursday",
        {"swaps": swaps, "attacks": attacks, "blocked": blocked, "pacts": pacts},
        pick_variant(league_id, week, "thursday"),
    )


def debrief(
    league_id: str,
    week: str,
    *,
    winner: str,
    pf: int,
    best: str,
    best_move: float,
    worst: str,
    worst_move: float,
    drone_pf: int,
    rusty: int,
) -> Dispatch:
    """Friday edition, after the debrief: everything can be named."""
    return Dispatch(
        "dispatch.debrief",
        {
            "winner": winner,
            "pf": pf,
            "best": best,
            "best_move": best_move,
            "worst": worst,
            "worst_move": worst_move,
            "drone_pf": drone_pf,
            "rusty": rusty,
        },
        pick_variant(league_id, week, "debrief"),
    )


# --- Python renderer (tests and PR preview; the app renders with its own i18n) ----------
_ENTRY = re.compile(r"'([\w.]+)':\s*(['\"])(.*?)(?<!\\)\2,", re.DOTALL)


@cache
def messages(language: str) -> Mapping[str, str]:
    text = (I18N_DIR / f"{language}.ts").read_text(encoding="utf-8")
    return {key: value.replace("\\'", "'") for key, _, value in _ENTRY.findall(text)}


def render(dispatch: Dispatch, language: str) -> str:
    template = messages(language)[f"{dispatch.template_key}.{dispatch.variant}"]
    return re.sub(r"\{(\w+)\}", lambda m: str(dispatch.vars.get(m.group(1), m.group(0))), template)
