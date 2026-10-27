"""Rounding used by every rule: half away from zero (GAME_RULES preamble).

Python's built-in round() is banker's rounding (round(2.5) == 2); never use it for game maths.
"""

import math


def round_half_away(value: float) -> int:
    """Round to the nearest integer, halves away from zero: 2.5 -> 3, -2.5 -> -3."""
    return int(math.copysign(math.floor(abs(value) + 0.5), value))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
