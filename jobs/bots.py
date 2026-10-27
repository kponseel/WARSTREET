"""Bot players for simulated games (`jobs.dev`). Never used by the cron.

A bot is a league member whose account email ends with BOT_EMAIL_DOMAIN. Bots act only
through the player RPCs, exactly like the app, so every rule and deadline is enforced by
the database. Their choices are seeded by (league, week, bot, window): replaying a window
gives the same decisions, and a move already made is never repeated (they check the
database first), so calling them on every simulated tick is safe.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from engine import config
from engine.drone import random_squad, seeded_rng
from jobs.db import Connection
from jobs.league_jobs import _load
from jobs.sim import as_user

log = logging.getLogger(__name__)

BOT_EMAIL_DOMAIN = "bots.warstreet.invalid"
ORDER_CHANCE = 0.6  # a bot plays one order in a window with this probability
PACT_CHANCE = 0.35  # proposes a pact at briefing
ACCEPT_CHANCE = 0.5  # accepts a pact proposed to it
SWAP_CHANCE = 0.5


@dataclass(frozen=True)
class Bot:
    user_id: str
    member_id: str
    pseudo: str
    commander: str | None


def bot_email(name: str) -> str:
    return f"{name.lower()}@{BOT_EMAIL_DOMAIN}"


def league_bots(conn: Connection, league_id: str) -> list[Bot]:
    rows = conn.execute(
        "select m.user_id, m.member_id, m.pseudo, m.commander::text as commander "
        "from public.league_members m join auth.users u on u.id = m.user_id "
        "where m.league_id = %s and u.email like %s order by m.joined_at",
        (league_id, f"%@{BOT_EMAIL_DOMAIN}"),
    ).fetchall()
    return [Bot(str(r["user_id"]), str(r["member_id"]), r["pseudo"], r["commander"]) for r in rows]


def _bump_clock(conn: Connection) -> None:
    """One second later for each move: orders resolve by play time, ties are avoided."""
    row = conn.execute("select current_setting('app.fake_now', true) as now").fetchone()
    if row and row["now"]:
        later = datetime.fromisoformat(row["now"]) + timedelta(seconds=1)
        conn.execute("select set_config('app.fake_now', %s, false)", (later.isoformat(),))
    else:
        conn.execute(
            "update private.dev_clock set fake_now = fake_now + interval '1 second' where id"
        )


def act(conn: Connection, bot: Bot, function: str, **params: Any) -> bool:
    _bump_clock(conn)
    what = params.get("p_type") or params.get("p_slot") or ""
    try:
        as_user(conn, bot.user_id, function, **params)
    except Exception as exc:  # a refused move is part of the game: log it and go on
        log.info("bot %s: %s %s refused (%s)", bot.pseudo, function, what, str(exc).splitlines()[0])
        return False
    log.info("bot %s: %s %s", bot.pseudo, function, what)
    return True


def _humans(conn: Connection, league_id: str) -> list[dict[str, Any]]:
    return conn.execute(
        "select member_id::text as member_id, commander::text as commander "
        "from public.league_members where league_id = %s and not is_drone",
        (league_id,),
    ).fetchall()


def _has_orders(conn: Connection, bot: Bot, week: date, window: str) -> bool:
    return (
        conn.execute(
            "select 1 from public.orders where member_id = %s and week = %s and order_window = %s",
            (bot.member_id, week, window),
        ).fetchone()
        is not None
    )


def _orders_for(window: str, commander: str | None) -> list[str]:
    forbidden = set(config.BERSERKER_FORBIDDEN_ORDERS) if commander == "berserker" else set()
    return sorted(
        code
        for code, spec in config.ORDERS.items()
        if window in spec["windows"] and code not in forbidden  # type: ignore[operator]
    )


def _play_order(conn: Connection, league_id: str, bot: Bot, week: date, window: str) -> None:
    rng = seeded_rng("bot-order", league_id, week, bot.pseudo, window)
    if _has_orders(conn, bot, week, window) or rng.random() >= ORDER_CHANCE:
        return
    code = rng.choice(_orders_for(window, bot.commander))
    params: dict[str, Any] = {"p_league": league_id, "p_type": code}
    if code in config.TARGETED_ORDERS:
        targets = [
            h
            for h in _humans(conn, league_id)
            if h["member_id"] != bot.member_id
            and not (code == "intel" and h["commander"] == "shadow")
        ]
        if not targets:
            return
        params["p_target_member"] = rng.choice(targets)["member_id"]
    if code in config.ORDERS_WITH_TARGET_SLOT:
        slots = [
            s for s in config.FRONT_SLOTS if not (code == "field_promotion" and s == "champion")
        ]
        params["p_target_slot"] = rng.choice(slots)
    act(conn, bot, "play_order", **params)


def play_briefing(conn: Connection, league_id: str, week: date) -> None:
    """Each bot drafts (once), may play one briefing order, propose and answer pacts."""
    data = _load(conn, league_id, week)
    for bot in league_bots(conn, league_id):
        rng = seeded_rng("bot-briefing", league_id, week, bot.pseudo)
        saved = conn.execute(
            "select 1 from public.squads where member_id = %s and week = %s and not auto",
            (bot.member_id, week),
        ).fetchone()
        if not saved and data.zone:
            squad = random_squad(rng, data.instruments, data.zone, bot.commander)
            act(conn, bot, "save_squad", p_league=league_id, p_units=squad)
        _play_order(conn, league_id, bot, week, "briefing")
        proposed = conn.execute(
            "select 1 from public.pacts where proposer_member_id = %s and week = %s",
            (bot.member_id, week),
        ).fetchone()
        if not proposed and rng.random() < PACT_CHANCE:
            partners = [h for h in _humans(conn, league_id) if h["member_id"] != bot.member_id]
            if partners:
                act(
                    conn,
                    bot,
                    "propose_pact",
                    p_league=league_id,
                    p_partner=rng.choice(partners)["member_id"],
                )
        for pact in conn.execute(
            "select id::text as id from public.pacts where partner_member_id = %s and week = %s "
            "and status = 'proposed' order by created_at",
            (bot.member_id, week),
        ).fetchall():
            answer = seeded_rng("bot-pact", pact["id"]).random() < ACCEPT_CHANCE
            act(conn, bot, "accept_pact" if answer else "decline_pact", p_pact=pact["id"])


def play_resupply(conn: Connection, league_id: str, week: date) -> None:
    """Each bot may swap one unit (a valid one) and play one resupply order."""
    for bot in league_bots(conn, league_id):
        rng = seeded_rng("bot-resupply", league_id, week, bot.pseudo)
        swapped = conn.execute(
            "select 1 from public.swaps where member_id = %s and week = %s",
            (bot.member_id, week),
        ).fetchone()
        if not swapped and rng.random() < SWAP_CHANCE:
            reserves = [
                r["slot"]
                for r in conn.execute(
                    "select slot::text as slot from public.squad_units where member_id = %s "
                    "and week = %s and slot::text like 'reserve%%'",
                    (bot.member_id, week),
                ).fetchall()
            ]
            pairs = [(f, r) for f in config.FRONT_SLOTS for r in reserves]
            rng.shuffle(pairs)
            for front, reserve in pairs[:6]:  # the first valid swap
                if act(
                    conn, bot, "swap_unit", p_league=league_id, p_slot=front, p_reserve_slot=reserve
                ):
                    break
        _play_order(conn, league_id, bot, week, "resupply")
