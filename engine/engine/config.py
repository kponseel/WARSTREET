"""Tunable values of the game (docs/GAME_RULES.md v2.1).

Every number of the rules lives here and nowhere else. `GAME_CONFIG` below is the
JSON-serialisable view of these values: `supabase/scripts/generate_seed.py` writes it to
the `game_config` table, which the RPC functions read for validation and the UI reads for
display. A test fails if the committed seed differs from this module.

The game name lives here and in web/src/config.ts only.
"""

from typing import Final

GAME_NAME: Final = "WARSTREET"

# --- §1 League lifecycle -------------------------------------------------------------
MIN_PLAYERS: Final = 3
MAX_PLAYERS: Final = 5
CAMPAIGN_WEEKS_DEFAULT: Final = 8
CAMPAIGN_WEEKS_MIN: Final = 4
CAMPAIGN_WEEKS_MAX: Final = 10
FINAL_WEEK_MULTIPLIER: Final = 2
INVITE_CODE_LENGTH: Final = 6
INVITE_CODE_ALPHABET: Final = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
PSEUDO_MIN_LENGTH: Final = 3
PSEUDO_MAX_LENGTH: Final = 16
LEAGUE_NAME_MAX_LENGTH: Final = 40
MIN_FIRST_BRIEFING_HOURS: Final = 12
AVATAR_COLORS: Final = (
    "#1f3a5f",
    "#c2410c",
    "#166534",
    "#7c3aed",
    "#b91c1c",
    "#0e7490",
    "#a16207",
    "#be185d",
)

# --- §2 The week (local times are Europe/Paris) -------------------------------------
TIMEZONE: Final = "Europe/Paris"
LOCK_LOCAL_TIME: Final = "23:59:59"  # Sunday before the week's Monday
RESUPPLY_CLOSE_LOCAL_TIME: Final = "08:59:59"  # Thursday
S2_START_LOCAL_TIME: Final = "09:00:00"  # Thursday
RESUPPLY_OPEN_DELAY_MIN: Final = 5  # after the last XNYS close on or before Wednesday
RESUPPLY_OPEN_FALLBACK_LOCAL_TIME: Final = "22:00:00"  # Wednesday, if no XNYS session
DEBRIEF_DELAY_MIN: Final = 30  # after the last XNYS close of the week
PRICE_CAPTURE_DELAY_MIN: Final = 10  # P0 / P_mid after the open
LIVE_PRICES_RETENTION_DAYS: Final = 14

# --- §3 Squad --------------------------------------------------------------------------
FRONT_SLOTS: Final = ("champion", "veteran", "marksman", "saboteur", "priority_target")
RESERVE_SLOTS: Final = ("reserve_1", "reserve_2", "reserve_3")
SLOT_MULTIPLIERS: Final = {
    "champion": 2.0,
    "veteran": 1.5,
    "marksman": 1.0,
    "saboteur": -1.0,
    "priority_target": 1.2,
}
FRONT_MIN_PER_REGION: Final = 2  # at least 2 EU and 2 US in the front
RESERVE_SIZE: Final = 2
RESERVE_MIN_PER_REGION: Final = 1  # at least 1 EU and 1 US in the reserve
MAX_SWAPS: Final = 1
REF_VOL: Final = 3.5
COEF_MIN: Final = 0.25
COEF_MAX: Final = 2.0
VOL_WEEKS: Final = 12
DISPLAY_CLASS_THRESHOLDS: Final = {"armored": 3.0, "infantry": 5.0, "commando": 9.0}
CONFLICT_ZONE_SIZE: Final = 8
WEATHER_ON_FIRE_MIN_RETURN: Final = 5.0
WEATHER_FROZEN_MAX_RETURN: Final = -5.0
WEATHER_ROLLER_COASTER_MIN_DAILY_MOVE: Final = 4.0

# --- §4 Scoring ------------------------------------------------------------------------
PF_PER_PERCENT: Final = 10
UNIT_PF_CLAMP: Final = 150
ELITE_UNIT_BONUS: Final = 10  # [calibrate]
CAMPAIGN_POINTS: Final = {  # [calibrate] by number of humans, 1st place first
    3: (10, 5, 2),
    4: (10, 6, 3, 1),
    5: (10, 7, 5, 3, 1),
}

# --- §5 Commanders ---------------------------------------------------------------------
COMMANDERS: Final = (
    "bastion",
    "berserker",
    "prophet",
    "hunter",
    "shadow",
    "technomancer",
    "quartermaster",
)
BASTION_LOSS_REDUCTION: Final = 5  # [calibrate]
BERSERKER_CHAMPION_MULTIPLIER: Final = 3.0
BERSERKER_FORBIDDEN_ORDERS: Final = ("force_field", "tactical_retreat")
PROPHET_SABOTEUR_MULTIPLIER: Final = -2.0
HUNTER_BONUS_PER_TARGET: Final = 6  # [calibrate]
HUNTER_BONUS_MAX: Final = 12  # [calibrate]
TECHNOMANCER_EXTRA_INCOME: Final = 1
TECHNOMANCER_AMMO_CAP: Final = 6
QUARTERMASTER_RESERVE_SIZE: Final = 3
QUARTERMASTER_MAX_SWAPS: Final = 2

# --- §6 Ammo and orders ----------------------------------------------------------------
AMMO_INCOME: Final = 3
AMMO_CAP: Final = 5
CATCH_UP_AMMO: Final = 1
BOUNTY_DISCOUNT: Final = 1
MIN_ORDER_COST: Final = 1
ATTACK_CAP_PER_WEEK: Final = 2
ORBITAL_STRIKE_FACTOR: Final = 0.5
PILLAGE_SHARE: Final = 0.30
REVERSAL_MARKSMAN_MULTIPLIER: Final = -1.0
ORDERS: Final = {
    "orbital_strike": {"kind": "attack", "cost": 2, "windows": ("resupply",)},
    "pillage": {"kind": "attack", "cost": 3, "windows": ("resupply",)},
    "blockade": {"kind": "attack", "cost": 2, "windows": ("briefing",)},
    "jamming": {"kind": "attack", "cost": 1, "windows": ("briefing", "resupply")},
    "force_field": {"kind": "defense", "cost": 1, "windows": ("briefing", "resupply")},
    "tactical_retreat": {"kind": "defense", "cost": 1, "windows": ("resupply",)},
    "field_promotion": {"kind": "maneuver", "cost": 2, "windows": ("resupply",)},
    "reversal": {"kind": "maneuver", "cost": 2, "windows": ("resupply",)},
    "intel": {"kind": "maneuver", "cost": 1, "windows": ("briefing",)},
}
ONCE_PER_WEEK_ORDERS: Final = ("field_promotion", "reversal", "tactical_retreat")
# Orders aimed at another player (the others target the player's own units).
TARGETED_ORDERS: Final = ("orbital_strike", "pillage", "blockade", "jamming", "intel")
# Orders that need a slot: another player's front slot, or one of the player's own.
ORDERS_WITH_TARGET_SLOT: Final = ("orbital_strike", "tactical_retreat", "field_promotion")

# --- §7 Pacts --------------------------------------------------------------------------
BETRAYAL_PENALTY: Final = -40
MAX_ACTIVE_PACTS_PER_WEEK: Final = 1

# --- §8 Feats and badges ---------------------------------------------------------------
FEATS: Final = {
    "total_victory": 60,
    "perfect_shot": 40,
    "resurrection": 40,
    "heavy_losses": -40,
}
RESURRECTION_PREV_MAX_RETURN: Final = -6.0
RESURRECTION_THIS_MIN_RETURN: Final = 4.0
HEAVY_LOSSES_MAX_RETURN: Final = -10.0
ORACLE_MIN_SABOTEUR_PF: Final = 50
CANNON_FODDER_PREV_MAX_RETURN: Final = -6.0
CANNON_FODDER_THIS_MAX_RETURN: Final = -5.0

# --- §10 Front Dispatch ----------------------------------------------------------------
# A Monday opening move larger than this (in %) is treated as a data artefact (a split or
# a bad quote between Friday's close and Monday's quote) and is never headlined.
DISPATCH_MAX_PLAUSIBLE_MOVE: Final = 40.0

# --- Security (ARCHITECTURE.md) ---------------------------------------------------------
# Player RPCs that write, per user and per minute (PostgREST pre-request hook). A person
# playing makes a few a minute; a script looping on an RPC is stopped.
RPC_RATE_LIMIT_PER_MINUTE: Final = 30

# --- Ops (status page) -----------------------------------------------------------------
# The tick runs every 15 min on weekdays (hourly at weekends) and pauses at night: no tick
# for this long means the cron is stopped (disabled workflow, Actions outage).
STATUS_TICK_LATE_AFTER_HOURS: Final = 8

# --- Mirror for the `game_config` table ------------------------------------------------
GAME_CONFIG: Final[dict[str, object]] = {
    "min_players": MIN_PLAYERS,
    "max_players": MAX_PLAYERS,
    "campaign_weeks_default": CAMPAIGN_WEEKS_DEFAULT,
    "campaign_weeks_min": CAMPAIGN_WEEKS_MIN,
    "campaign_weeks_max": CAMPAIGN_WEEKS_MAX,
    "final_week_multiplier": FINAL_WEEK_MULTIPLIER,
    "invite_code_length": INVITE_CODE_LENGTH,
    "invite_code_alphabet": INVITE_CODE_ALPHABET,
    "pseudo_min_length": PSEUDO_MIN_LENGTH,
    "pseudo_max_length": PSEUDO_MAX_LENGTH,
    "league_name_max_length": LEAGUE_NAME_MAX_LENGTH,
    "min_first_briefing_hours": MIN_FIRST_BRIEFING_HOURS,
    "avatar_colors": list(AVATAR_COLORS),
    "timezone": TIMEZONE,
    "lock_local_time": LOCK_LOCAL_TIME,
    "resupply_close_local_time": RESUPPLY_CLOSE_LOCAL_TIME,
    "s2_start_local_time": S2_START_LOCAL_TIME,
    "resupply_open_delay_min": RESUPPLY_OPEN_DELAY_MIN,
    "resupply_open_fallback_local_time": RESUPPLY_OPEN_FALLBACK_LOCAL_TIME,
    "debrief_delay_min": DEBRIEF_DELAY_MIN,
    "price_capture_delay_min": PRICE_CAPTURE_DELAY_MIN,
    "live_prices_retention_days": LIVE_PRICES_RETENTION_DAYS,
    "front_slots": list(FRONT_SLOTS),
    "reserve_slots": list(RESERVE_SLOTS),
    "slot_multipliers": SLOT_MULTIPLIERS,
    "front_min_per_region": FRONT_MIN_PER_REGION,
    "reserve_size": RESERVE_SIZE,
    "reserve_min_per_region": RESERVE_MIN_PER_REGION,
    "max_swaps": MAX_SWAPS,
    "ref_vol": REF_VOL,
    "coef_min": COEF_MIN,
    "coef_max": COEF_MAX,
    "vol_weeks": VOL_WEEKS,
    "display_class_thresholds": DISPLAY_CLASS_THRESHOLDS,
    "conflict_zone_size": CONFLICT_ZONE_SIZE,
    "weather_on_fire_min_return": WEATHER_ON_FIRE_MIN_RETURN,
    "weather_frozen_max_return": WEATHER_FROZEN_MAX_RETURN,
    "weather_roller_coaster_min_daily_move": WEATHER_ROLLER_COASTER_MIN_DAILY_MOVE,
    "pf_per_percent": PF_PER_PERCENT,
    "unit_pf_clamp": UNIT_PF_CLAMP,
    "elite_unit_bonus": ELITE_UNIT_BONUS,
    "campaign_points": {str(n): list(points) for n, points in CAMPAIGN_POINTS.items()},
    "commanders": list(COMMANDERS),
    "bastion_loss_reduction": BASTION_LOSS_REDUCTION,
    "berserker_champion_multiplier": BERSERKER_CHAMPION_MULTIPLIER,
    "berserker_forbidden_orders": list(BERSERKER_FORBIDDEN_ORDERS),
    "prophet_saboteur_multiplier": PROPHET_SABOTEUR_MULTIPLIER,
    "hunter_bonus_per_target": HUNTER_BONUS_PER_TARGET,
    "hunter_bonus_max": HUNTER_BONUS_MAX,
    "technomancer_extra_income": TECHNOMANCER_EXTRA_INCOME,
    "technomancer_ammo_cap": TECHNOMANCER_AMMO_CAP,
    "quartermaster_reserve_size": QUARTERMASTER_RESERVE_SIZE,
    "quartermaster_max_swaps": QUARTERMASTER_MAX_SWAPS,
    "ammo_income": AMMO_INCOME,
    "ammo_cap": AMMO_CAP,
    "catch_up_ammo": CATCH_UP_AMMO,
    "bounty_discount": BOUNTY_DISCOUNT,
    "min_order_cost": MIN_ORDER_COST,
    "attack_cap_per_week": ATTACK_CAP_PER_WEEK,
    "orbital_strike_factor": ORBITAL_STRIKE_FACTOR,
    "pillage_share": PILLAGE_SHARE,
    "reversal_marksman_multiplier": REVERSAL_MARKSMAN_MULTIPLIER,
    "orders": {
        code: {"kind": spec["kind"], "cost": spec["cost"], "windows": list(spec["windows"])}
        for code, spec in ORDERS.items()
    },
    "once_per_week_orders": list(ONCE_PER_WEEK_ORDERS),
    "targeted_orders": list(TARGETED_ORDERS),
    "orders_with_target_slot": list(ORDERS_WITH_TARGET_SLOT),
    "betrayal_penalty": BETRAYAL_PENALTY,
    "max_active_pacts_per_week": MAX_ACTIVE_PACTS_PER_WEEK,
    "feats": FEATS,
    "resurrection_prev_max_return": RESURRECTION_PREV_MAX_RETURN,
    "resurrection_this_min_return": RESURRECTION_THIS_MIN_RETURN,
    "heavy_losses_max_return": HEAVY_LOSSES_MAX_RETURN,
    "oracle_min_saboteur_pf": ORACLE_MIN_SABOTEUR_PF,
    "cannon_fodder_prev_max_return": CANNON_FODDER_PREV_MAX_RETURN,
    "cannon_fodder_this_max_return": CANNON_FODDER_THIS_MAX_RETURN,
    "dispatch_max_plausible_move": DISPATCH_MAX_PLAUSIBLE_MOVE,
    "rpc_rate_limit_per_minute": RPC_RATE_LIMIT_PER_MINUTE,
    "status_tick_late_after_hours": STATUS_TICK_LATE_AFTER_HOURS,
}
