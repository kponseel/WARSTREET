"""Unit weather flags, display only (GAME_RULES §3)."""

from __future__ import annotations

from engine import config


def weather_flags(
    prev_week_return: float | None,
    earnings_this_week: bool,
    max_abs_daily_move_prev: float | None,
) -> list[str]:
    flags: list[str] = []
    if prev_week_return is not None and prev_week_return >= config.WEATHER_ON_FIRE_MIN_RETURN:
        flags.append("on_fire")
    if prev_week_return is not None and prev_week_return <= config.WEATHER_FROZEN_MAX_RETURN:
        flags.append("frozen")
    if earnings_this_week:
        flags.append("earnings")
    if (
        max_abs_daily_move_prev is not None
        and max_abs_daily_move_prev >= config.WEATHER_ROLLER_COASTER_MIN_DAILY_MOVE
    ):
        flags.append("roller_coaster")
    return flags
