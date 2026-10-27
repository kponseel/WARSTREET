"""Dev mode: play whole games on a LOCAL database with bots and a simulated clock.

    python -m jobs.dev league [--bots 4] [--me you@example.test] [--week last|next|2026-W43]
                              [--weeks 4] [--lobby] [--prices auto|real|synthetic]
    python -m jobs.dev advance --league ID --to lock|monday|resupply|thursday|friday|debrief|
                                                next|end|2026-11-13T21:00Z [--no-bots]
    python -m jobs.dev clock [--at ISO | --clear]
    python -m jobs.dev inspect --league ID
    python -m jobs.dev logs [--last 5] [--errors]

How it works: a row in private.dev_clock makes the whole database (the app's RPCs too) run
at a simulated time (migration 12). `advance` steps that clock through every instant where
something happens (captures, phases, dispatches, debrief), lets the bots play their
briefing and resupply moves through the real RPCs, and runs the same `tick` as the cron at
each step. Prices: real Yahoo bars for weeks that are over (cached in .cache/prices/),
synthetic ones for weeks that have not happened yet.

`--me EMAIL` puts a real local account in the league (log in once in the app first; the
login code is in Mailpit, http://127.0.0.1:54324), so the UI can be played at any phase.

Safety: refuses any database that is not on localhost unless --allow-remote is given.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from engine import config
from engine.calendar import first_open, local_instant, phase_timestamps
from jobs import bots
from jobs.db import Connection, connect
from jobs.logs import setup_logging
from jobs.market import HISTORY_WEEKS
from jobs.market_jobs import bootstrap_week_stats, instruments
from jobs.prices import PriceProvider, default_provider
from jobs.sim import (
    DiskCache,
    HistoricalProvider,
    SyntheticMarket,
    as_user,
    briefing_opens,
    last_complete_week,
    parse_week,
    set_fake_now,
    week_instants,
)
from jobs.tick import TickFailed, tick

log = logging.getLogger("jobs.dev")

LOCAL_DB = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"  # `supabase start`
BOT_NAMES = ("Vega", "Orion", "Nyx", "Kestrel", "Ronin")
COLORS = config.AVATAR_COLORS[:-1]  # the last colour is the Drone's


# --- clock ----------------------------------------------------------------------------------
def get_clock(conn: Connection) -> datetime | None:
    row = conn.execute("select fake_now from private.dev_clock where id").fetchone()
    return row["fake_now"] if row else None


def set_clock(conn: Connection, at: datetime | None) -> None:
    with conn.transaction():
        conn.execute("delete from private.dev_clock")
        if at is not None:
            conn.execute("insert into private.dev_clock (fake_now) values (%s)", (at,))
    set_fake_now(conn, None)  # this session follows the dev clock too


def now_of(conn: Connection) -> datetime:
    return get_clock(conn) or datetime.now(UTC)


# --- prices ---------------------------------------------------------------------------------
def campaign_is_over(conn: Connection, monday: date) -> bool:
    """True when every week of the leagues playing `monday` is already in the past."""
    row = conn.execute(
        "select max(l.start_week + 7 * (l.campaign_weeks - 1)) as last_week "
        "from public.leagues l join public.weeks w on w.league_id = l.id where w.week = %s",
        (monday,),
    ).fetchone()
    last_week = row["last_week"] if row and row["last_week"] else monday
    return bool(last_week <= last_complete_week(datetime.now(UTC).date()))


def provider_for(conn: Connection, monday: date, mode: str) -> HistoricalProvider:
    # One source per campaign: real bars only when the whole campaign is over, so a price
    # level never jumps from real to synthetic between two weeks.
    synthetic = mode == "synthetic" or (mode == "auto" and not campaign_is_over(conn, monday))
    base: PriceProvider = SyntheticMarket() if synthetic else DiskCache(default_provider())
    start = monday - timedelta(weeks=HISTORY_WEEKS + 2)
    end = monday + timedelta(days=6)
    provider = HistoricalProvider(base, start, end)
    provider.mics = {i.ticker: i.calendar_mic for i in instruments(conn)}
    log.info("prices for %s: %s", monday, "synthetic" if synthetic else "real (cached)")
    return provider


# --- league ---------------------------------------------------------------------------------
def _ensure_bot_user(conn: Connection, name: str, run: str) -> str:
    email = bots.bot_email(f"{name}-{run}")
    user_id = str(uuid.uuid4())
    conn.execute(
        "insert into auth.users (id, email) values (%s, %s)",
        (user_id, email),
    )
    return user_id


def _user_by_email(conn: Connection, email: str) -> str:
    row = conn.execute("select id from auth.users where email = %s", (email.lower(),)).fetchone()
    if row is None:
        raise SystemExit(
            f"no account for {email}: log in once in the app with it (code in Mailpit), "
            "then run this command again"
        )
    return str(row["id"])


def create_league(
    conn: Connection,
    *,
    monday: date,
    bot_count: int,
    me: Sequence[str],
    weeks: int,
    start: bool,
    prices: str,
) -> dict[str, Any]:
    """A league whose week 1 is `monday`, created on the Wednesday before at 09:00 Paris."""
    set_clock(conn, local_instant(monday - timedelta(days=5), "09:00:00"))
    run = uuid.uuid4().hex[:6]
    players: list[tuple[str, str, str]] = []  # (user id, pseudo, commander)
    for email in me:
        # The pseudo is the start of the email (3 to 16 characters, like the app asks).
        pseudo = (email.split("@")[0] + "xxx")[: config.PSEUDO_MAX_LENGTH]
        players.append((_user_by_email(conn, email), pseudo, "hunter"))
    commanders = config.COMMANDERS
    for index in range(bot_count):
        name = BOT_NAMES[index % len(BOT_NAMES)]
        players.append(
            (_ensure_bot_user(conn, name, run), name, commanders[index % len(commanders)])
        )
    if not 0 < len(players) <= config.MAX_PLAYERS:
        raise SystemExit(
            f"a league has 1 to {config.MAX_PLAYERS} players here (got {len(players)})"
        )
    (host_id, host_pseudo, host_commander), *others = players
    league_id = str(
        as_user(
            conn,
            host_id,
            "create_league",
            p_name=f"Dev {monday.isoformat()} {run}",
            p_max_players=config.MAX_PLAYERS,
            p_campaign_weeks=weeks,
            p_drone_enabled=True,
            p_pseudo=host_pseudo,
            p_commander=host_commander,
            p_avatar_color=COLORS[0],
        )
    )
    code = conn.execute(
        "select invite_code from public.leagues where id = %s", (league_id,)
    ).fetchone()["invite_code"]  # type: ignore[index]
    for index, (user_id, pseudo, commander) in enumerate(others, start=1):
        as_user(
            conn,
            user_id,
            "join_league",
            p_code=code,
            p_pseudo=pseudo,
            p_commander=commander,
            p_avatar_color=COLORS[index % len(COLORS)],
        )
    for user_id, _, _ in players:
        as_user(conn, user_id, "set_ready", p_league=league_id, p_ready=True)
    if start:
        if len(players) < config.MIN_PLAYERS:
            raise SystemExit(f"starting needs {config.MIN_PLAYERS} players: add --bots")
        as_user(conn, host_id, "start_campaign", p_league=league_id)
        provider = provider_for(conn, monday, prices)
        provider.now = now_of(conn)
        bootstrap_week_stats(conn, provider, monday)  # this week's Conflict Zone
    return {"league_id": league_id, "invite_code": code, "week": monday.isoformat()}


# --- advancing time --------------------------------------------------------------------------
def current_week(conn: Connection, league_id: str) -> dict[str, Any]:
    row = conn.execute(
        "select * from public.weeks where league_id = %s order by week desc limit 1", (league_id,)
    ).fetchone()
    if row is None:
        raise SystemExit("this league has not started")
    return row


def target_instant(conn: Connection, league_id: str, target: str) -> datetime:
    week = current_week(conn, league_id)
    monday: date = week["week"]
    ts = phase_timestamps(monday)
    named = {
        "briefing": briefing_opens(monday) + timedelta(minutes=5),
        "lock": ts.lock_at + timedelta(minutes=1),
        "monday": (first_open("XPAR", monday) or ts.lock_at)
        + timedelta(minutes=config.PRICE_CAPTURE_DELAY_MIN + 5),
        "resupply": ts.resupply_opens_at + timedelta(minutes=10),
        "thursday": local_instant(monday + timedelta(days=3), "09:30:00"),
        "friday": local_instant(monday + timedelta(days=4), "18:00:00"),
        "debrief": ts.debrief_at + timedelta(minutes=50),
        "next": briefing_opens(monday + timedelta(days=7)) + timedelta(minutes=5),
    }
    if target in named:
        return named[target]
    if target == "end":
        remaining = conn.execute(
            "select l.campaign_weeks - w.number as left from public.leagues l "
            "join public.weeks w on w.league_id = l.id where l.id = %s and w.week = %s",
            (league_id, monday),
        ).fetchone()
        weeks_left = int(remaining["left"]) if remaining else 0
        return phase_timestamps(monday + timedelta(days=7 * weeks_left)).debrief_at + timedelta(
            minutes=50
        )
    return parse_instant(target)


def _instants_between(start: datetime, end: datetime) -> list[datetime]:
    monday = start.date() - timedelta(days=start.date().weekday())
    result: set[datetime] = set()
    week = monday - timedelta(days=7)
    while week <= end.date() + timedelta(days=7):
        result |= {i for i in week_instants(week) if start < i <= end}
        week += timedelta(days=7)
    result.add(end)
    return sorted(result)


def advance(
    conn: Connection,
    league_id: str,
    to: datetime,
    *,
    play_bots: bool = True,
    prices: str = "auto",
    echo: bool = True,
) -> list[str]:
    """Steps the dev clock to `to`, with bots playing and a tick at every instant."""
    start = now_of(conn)
    if to <= start:
        raise SystemExit(f"the clock is already at {start.isoformat()}")
    providers: dict[date, HistoricalProvider] = {}
    lines: list[str] = []
    for instant in _instants_between(start, to):
        set_clock(conn, instant)
        week = current_week(conn, league_id)
        monday: date = week["week"]
        provider = providers.get(monday) or providers.setdefault(
            monday, provider_for(conn, monday, prices)
        )
        provider.now = instant
        if play_bots:
            if briefing_opens(monday) <= instant < week["lock_at"]:
                bots.play_briefing(conn, league_id, monday)
            elif (
                week["resupply_opens_at"]
                and week["resupply_opens_at"] <= instant < week["resupply_closes_at"]
            ):
                bots.play_resupply(conn, league_id, monday)
            set_clock(conn, instant)  # bots moved the clock by a few seconds
        try:
            done = tick(conn, provider, instant, league_ids=[league_id])
        except TickFailed as failure:
            log.error(
                "tick at %s failed: %s (see `python -m jobs.dev logs --errors`)", instant, failure
            )
            raise SystemExit(1) from failure
        for line in done:
            if "live_" not in line:
                lines.append(f"{instant.isoformat()} {line}")
                if echo:
                    print(f"{instant:%a %d %b %H:%M}Z  {line}")
    return lines


# --- inspection ------------------------------------------------------------------------------
def inspect(conn: Connection, league_id: str) -> dict[str, Any]:
    league = conn.execute(
        "select id, name, status, invite_code, campaign_weeks, start_week from public.leagues "
        "where id = %s",
        (league_id,),
    ).fetchone()
    if league is None:
        raise SystemExit("no such league")
    week = conn.execute(
        "select week, number, phase, lock_at, resupply_opens_at, resupply_closes_at, debrief_at "
        "from public.weeks where league_id = %s order by week desc limit 1",
        (league_id,),
    ).fetchone()
    monday = week["week"] if week else None
    members = conn.execute(
        "select m.pseudo, m.commander, m.is_drone, coalesce(a.balance, 0) as ammo, "
        "s.locked, s.auto, sl.pf_live, sl.rank_live, sf.pf_total, sf.rank, sf.campaign_points "
        "from public.league_members m "
        "left join public.ammo_balance a on a.member_id = m.member_id "
        "left join public.squads s on s.member_id = m.member_id and s.week = %(w)s "
        "left join public.scores_live_public sl on sl.member_id = m.member_id and sl.week = %(w)s "
        "left join public.scores_final sf on sf.member_id = m.member_id and sf.week = %(w)s "
        "where m.league_id = %(l)s order by m.joined_at",
        {"l": league_id, "w": monday},
    ).fetchall()
    orders = conn.execute(
        "select m.pseudo, o.type, t.pseudo as target, o.target_slot, o.order_window, o.status "
        "from public.orders o join public.league_members m on m.member_id = o.member_id "
        "left join public.league_members t on t.member_id = o.target_member_id "
        "where o.league_id = %s and o.week = %s order by o.created_at",
        (league_id, monday),
    ).fetchall()
    pacts = conn.execute(
        "select a.pseudo as proposer, b.pseudo as partner, p.status from public.pacts p "
        "join public.league_members a on a.member_id = p.proposer_member_id "
        "join public.league_members b on b.member_id = p.partner_member_id "
        "where p.league_id = %s and p.week = %s",
        (league_id, monday),
    ).fetchall()
    runs = conn.execute(
        "select week, transition from public.job_runs where league_id = %s order by week, ran_at",
        (league_id,),
    ).fetchall()
    events = conn.execute(
        "select ts, kind, template_key, vars from public.events where league_id = %s "
        "order by ts desc, id desc limit 8",
        (league_id,),
    ).fetchall()
    return {
        "clock": now_of(conn).isoformat(),
        "dev_clock": get_clock(conn) is not None,
        "league": league,
        "week": week,
        "members": members,
        "orders": orders,
        "pacts": pacts,
        "job_runs": [f"{r['week']} {r['transition']}" for r in runs],
        "events": events,
    }


def tick_logs(conn: Connection, last: int, errors_only: bool) -> list[dict[str, Any]]:
    return conn.execute(
        "select id, started_at, game_time, ok, done, error, "
        "(select jsonb_agg(e) from jsonb_array_elements(log) e "
        " where not %(errors)s or e->>'level' in ('warning', 'error')) as log "
        "from private.tick_runs where not %(errors)s or not ok "
        "order by id desc limit %(last)s",
        {"errors": errors_only, "last": last},
    ).fetchall()


# --- CLI -------------------------------------------------------------------------------------
def _db_url(args: argparse.Namespace) -> str:
    url = args.db or os.environ.get("WARSTREET_DEV_DB_URL") or LOCAL_DB
    host = urlparse(url).hostname or ""
    if host not in ("127.0.0.1", "localhost", "::1") and not args.allow_remote:
        raise SystemExit("jobs.dev only runs on a local database (use --allow-remote to insist)")
    return url


def _week_arg(value: str) -> date:
    today = datetime.now(UTC).date()
    if value == "last":
        return last_complete_week(today)
    if value == "next":
        return today - timedelta(days=today.weekday()) + timedelta(days=7)
    return parse_week(value)


def _print(data: Any) -> None:
    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dev mode: simulated games on a local database")
    parser.add_argument("--db", help=f"Postgres URL (default {LOCAL_DB} or $WARSTREET_DEV_DB_URL)")
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--log-format", choices=("text", "json"), default="text")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    parser.add_argument("--json", action="store_true", help="print only a JSON result (scripts)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("league", help="create a league with bots (and you)")
    p.add_argument("--bots", type=int, default=3)
    p.add_argument("--me", action="append", default=[], help="a local account to add (repeat)")
    p.add_argument("--week", type=_week_arg, default=_week_arg("last"))
    p.add_argument("--weeks", type=int, default=config.CAMPAIGN_WEEKS_MIN)
    p.add_argument("--lobby", action="store_true", help="stay in the lobby (do not start)")
    p.add_argument("--prices", choices=("auto", "real", "synthetic"), default="auto")
    p.add_argument("--no-bots", action="store_true", help="bots do not draft at briefing")

    p = sub.add_parser("advance", help="step the clock, bots play, ticks run")
    p.add_argument("--league", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--no-bots", action="store_true")
    p.add_argument("--prices", choices=("auto", "real", "synthetic"), default="auto")

    p = sub.add_parser("clock", help="show, set or clear the dev clock")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--at")
    group.add_argument("--clear", action="store_true")

    p = sub.add_parser("inspect", help="the state of a league (JSON)")
    p.add_argument("--league", required=True)

    p = sub.add_parser("logs", help="the last ticks with their log lines")
    p.add_argument("--last", type=int, default=5)
    p.add_argument("--errors", action="store_true", help="failed ticks, warnings and errors only")

    args = parser.parse_args(argv)
    setup_logging(
        args.log_format, logging.DEBUG if args.verbose else logging.INFO, quiet=not args.verbose
    )
    with connect(_db_url(args)) as conn:
        if args.command == "league":
            result = create_league(
                conn,
                monday=args.week,
                bot_count=args.bots,
                me=args.me,
                weeks=args.weeks,
                start=not args.lobby,
                prices=args.prices,
            )
            if not args.lobby:
                advance(
                    conn,
                    result["league_id"],
                    briefing_opens(args.week) + timedelta(minutes=5),
                    play_bots=not args.no_bots,
                    prices=args.prices,
                    echo=not args.json,
                )
            result["clock"] = now_of(conn).isoformat()
            if args.json:
                print(json.dumps(result))
            else:
                _print(result)
                print(
                    f"\nNext: python -m jobs.dev advance --league {result['league_id']} --to lock\n"
                    "App: http://127.0.0.1:5173 (login code in Mailpit, http://127.0.0.1:54324)"
                )
        elif args.command == "advance":
            to = target_instant(conn, args.league, args.to)
            lines = advance(
                conn,
                args.league,
                to,
                play_bots=not args.no_bots,
                prices=args.prices,
                echo=not args.json,
            )
            clock = now_of(conn).isoformat()
            summary = {"clock": clock, "transitions": lines}
            print(json.dumps(summary) if args.json else f"clock: {clock}")
        elif args.command == "clock":
            if args.clear:
                set_clock(conn, None)
            elif args.at:
                set_clock(conn, parse_instant(args.at))
            print(
                json.dumps({"clock": now_of(conn).isoformat(), "dev": get_clock(conn) is not None})
            )
        elif args.command == "inspect":
            _print(inspect(conn, args.league))
        elif args.command == "logs":
            _print(tick_logs(conn, args.last, args.errors))
    return 0


def parse_instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


if __name__ == "__main__":
    raise SystemExit(main())
