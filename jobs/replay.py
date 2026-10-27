"""Replay a past week end to end, in minutes, with real daily bars and a fake clock.

    python -m jobs.replay --league demo --week 2026-W43 [--db URL] [--out /tmp/replay.json]

`--league demo` creates a demo league (4 bots + the Drone) whose first week is the replayed
one; `--league <uuid>` replays a league that already has that week. The tool then walks
the fake clock through every transition of the week (briefing, lock, opens, resupply,
Thursday, the closes, the debrief) and calls the same `tick` as the cron, so the result is
what the real jobs would have produced. Bots play a few orders so the Dispatches have
something to say. Prices come from the normal provider (Yahoo), fetched once per ticker
and cut at the fake clock; a live quote is a straight line from the session open to its
close (no intraday bars).

Use a local or dev database: the demo league and its data stay there. The fake clock
(`app.fake_now`) only works for a direct Postgres connection, never through the API.
"""

from __future__ import annotations

import argparse
import json
import logging
import uuid
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from engine import config
from engine.calendar import phase_timestamps
from engine.drone import random_squad, seeded_rng
from jobs import dispatch
from jobs.db import Connection, connect
from jobs.league_jobs import _load
from jobs.logs import setup_logging
from jobs.market import HISTORY_WEEKS
from jobs.market_jobs import bootstrap_week_stats, instruments
from jobs.prices import PriceProvider, default_provider
from jobs.sim import HistoricalProvider, as_user, briefing_opens, parse_week, week_instants
from jobs.sim import set_fake_now as set_clock
from jobs.tick import tick

__all__ = ["parse_week", "replay"]

log = logging.getLogger(__name__)

BOTS = (("Vega", "bastion"), ("Orion", "hunter"), ("Nyx", "shadow"), ("Kestrel", "berserker"))
COLORS = ("#1f3a5f", "#c2410c", "#166534", "#7c3aed")
DEMO_CAMPAIGN_WEEKS = config.CAMPAIGN_WEEKS_MIN


# --- demo league ---------------------------------------------------------------------------
def try_order(conn: Connection, user_id: str, function: str, **params: Any) -> bool:
    """One bot move, one second after the previous one (orders resolve by play time)."""
    row = conn.execute("select current_setting('app.fake_now') as now").fetchone()
    if row and row["now"]:
        set_clock(conn, datetime.fromisoformat(row["now"]) + timedelta(seconds=1))
    try:
        as_user(conn, user_id, function, **params)
    except Exception as exc:  # a refused bot move is fine: the replay goes on
        log.info("bot %s refused: %s", function, str(exc).splitlines()[0])
        return False
    log.info("bot %s %s", function, params.get("p_type", params.get("p_slot", "")))
    return True


@dataclass
class Demo:
    league_id: str
    users: dict[str, str]  # pseudo -> user id
    members: dict[str, str]  # pseudo -> member id


def create_demo(conn: Connection, monday: date) -> Demo:
    """A demo league whose first week is `monday` (created the Wednesday before)."""
    set_clock(conn, datetime.combine(monday - timedelta(days=5), datetime.min.time(), UTC))
    users: dict[str, str] = {}
    for pseudo, _ in BOTS:
        user_id = str(uuid.uuid4())
        conn.execute(
            "insert into auth.users (id, email) values (%s, %s)",
            (user_id, f"demo-{user_id[:12]}@example.invalid"),
        )
        users[pseudo] = user_id
    (host, commander), *others = BOTS
    league_id = str(
        as_user(
            conn,
            users[host],
            "create_league",
            p_name=f"Replay {monday.isoformat()}",
            p_max_players=len(BOTS) + 1,
            p_campaign_weeks=DEMO_CAMPAIGN_WEEKS,
            p_drone_enabled=True,
            p_pseudo=host,
            p_commander=commander,
            p_avatar_color=COLORS[0],
        )
    )
    code = conn.execute(
        "select invite_code from public.leagues where id = %s", (league_id,)
    ).fetchone()
    for index, (pseudo, commander) in enumerate(others, start=1):
        as_user(
            conn,
            users[pseudo],
            "join_league",
            p_code=code["invite_code"] if code else "",
            p_pseudo=pseudo,
            p_commander=commander,
            p_avatar_color=COLORS[index],
        )
    for user_id in users.values():
        as_user(conn, user_id, "set_ready", p_league=league_id, p_ready=True)
    as_user(conn, users[host], "start_campaign", p_league=league_id)
    rows = conn.execute(
        "select user_id, member_id from public.league_members where league_id = %s",
        (league_id,),
    ).fetchall()
    by_user = {str(r["user_id"]): str(r["member_id"]) for r in rows if r["user_id"]}
    return Demo(league_id, users, {p: by_user[u] for p, u in users.items()})


def briefing_moves(conn: Connection, demo: Demo, monday: date) -> None:
    """Bots save a squad (except Kestrel, who forgets: auto squad at lock) and play orders."""
    data = _load(conn, demo.league_id, monday)
    commanders = {p: c for p, c in BOTS}
    for pseudo in ("Vega", "Orion", "Nyx"):
        rng = seeded_rng("replay", monday.isoformat(), pseudo)
        squad = random_squad(rng, data.instruments, data.zone, commanders[pseudo])
        try_order(conn, demo.users[pseudo], "save_squad", p_league=demo.league_id, p_units=squad)
    try_order(conn, demo.users["Vega"], "play_order", p_league=demo.league_id, p_type="force_field")
    for target in ("Vega", "Nyx"):  # the first is blocked by the force field
        try_order(
            conn,
            demo.users["Orion"],
            "play_order",
            p_league=demo.league_id,
            p_type="jamming",
            p_target_member=demo.members[target],
        )


def resupply_moves(conn: Connection, demo: Demo) -> None:
    for reserve in ("reserve_1", "reserve_2"):  # the one that keeps the front valid
        if try_order(
            conn,
            demo.users["Kestrel"],
            "swap_unit",
            p_league=demo.league_id,
            p_slot="marksman",
            p_reserve_slot=reserve,
        ):
            break
    try_order(
        conn,
        demo.users["Vega"],
        "play_order",
        p_league=demo.league_id,
        p_type="orbital_strike",
        p_target_member=demo.members["Orion"],
        p_target_slot="champion",
    )


def _moves(
    monday: date, demo: Demo | None, conn: Connection
) -> Iterator[tuple[datetime, Callable[[], None]]]:
    if demo is None:
        return
    ts = phase_timestamps(monday)
    saturday = briefing_opens(monday)
    yield saturday + timedelta(minutes=5), lambda: briefing_moves(conn, demo, monday)
    yield ts.resupply_opens_at + timedelta(minutes=5), lambda: resupply_moves(conn, demo)


def replay(conn: Connection, base: PriceProvider, monday: date, league: str) -> dict[str, Any]:
    start = monday - timedelta(weeks=HISTORY_WEEKS + 2)
    provider = HistoricalProvider(base, start, monday + timedelta(days=6))
    provider.mics = {i.ticker: i.calendar_mic for i in instruments(conn)}
    demo = create_demo(conn, monday) if league == "demo" else None
    league_id = demo.league_id if demo else league
    provider.now = datetime.combine(monday - timedelta(days=3), datetime.min.time(), UTC)
    bootstrap_week_stats(conn, provider, monday)  # the Conflict Zone of the replayed week
    moves = sorted(_moves(monday, demo, conn), key=lambda m: m[0])
    instants = sorted(set(week_instants(monday)) | {at for at, _ in moves})
    actions = dict(moves)
    lines: list[str] = []
    for now in instants:
        provider.now = now
        set_clock(conn, now)
        if now in actions:
            actions[now]()
            continue
        for line in tick(conn, provider, now, league_ids=[league_id]):
            if "live_" not in line:
                lines.append(f"{now.isoformat()} {line}")
                log.info("%s %s", now.isoformat(), line)
    conn.execute("select set_config('app.fake_now', '', false)")
    return summary(conn, league_id, monday, lines)


def summary(conn: Connection, league_id: str, monday: date, lines: list[str]) -> dict[str, Any]:
    scores = conn.execute(
        "select m.pseudo, m.commander::text as commander, s.pf_total, s.rank, "
        "s.campaign_points::float as campaign_points from public.scores_final s "
        "join public.league_members m on m.member_id = s.member_id "
        "where s.league_id = %s and s.week = %s order by s.rank nulls last, m.pseudo",
        (league_id, monday),
    ).fetchall()
    badges = conn.execute(
        "select m.pseudo, b.code from public.badges b join public.league_members m "
        "on m.member_id = b.member_id where b.league_id = %s and b.week = %s order by 1, 2",
        (league_id, monday),
    ).fetchall()
    events = conn.execute(
        "select template_key, vars, variant from public.events where league_id = %s "
        "and week = %s and kind = 'dispatch' order by ts, id",
        (league_id, monday),
    ).fetchall()
    dispatches = []
    for event in events:
        item = dispatch.Dispatch(event["template_key"], event["vars"], event["variant"])
        dispatches.append(
            {
                "template_key": item.template_key,
                "variant": item.variant,
                "vars": item.vars,
                "en": dispatch.render(item, "en"),
                "fr": dispatch.render(item, "fr"),
            }
        )
    return {
        "league_id": league_id,
        "week": monday.isoformat(),
        "transitions": lines,
        "scores": scores,
        "badges": badges,
        "dispatches": dispatches,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay a past week with real prices")
    parser.add_argument("--league", required=True, help="'demo' or an existing league id")
    parser.add_argument("--week", required=True, type=parse_week, help="2026-W43 or a date")
    parser.add_argument("--db", default=None, help="Postgres URL (default: $SUPABASE_DB_URL)")
    parser.add_argument("--out", type=Path, default=None, help="write the summary as JSON")
    args = parser.parse_args(argv)
    setup_logging()
    with connect(args.db) as conn:
        result = replay(conn, default_provider(), args.week, args.league)
    for row in result["scores"]:
        print(
            f"#{row['rank'] or '-'} {row['pseudo']:<8} {row['commander'] or 'drone':<12} "
            f"PF {row['pf_total']:>5}  CP {row['campaign_points']:g}"
        )
    for item in result["dispatches"]:
        print(f"\n[{item['template_key']}]\nEN: {item['en']}\nFR: {item['fr']}")
    if args.out:
        args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
