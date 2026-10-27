"""League transitions (docs/ARCHITECTURE.md §6), keyed in `job_runs`.

For each active league, the latest week is moved forward according to "what should be
true now" (its stored phase timestamps): open_briefing, lock, open_resupply,
close_resupply, the Front Dispatch editions and the debrief. `live_scores` is not keyed: it
is recomputed every tick between lock and debrief. All maths come from engine/.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from psycopg.types.json import Jsonb

from engine import config
from engine.calendar import first_open, local_instant, phase_timestamps
from engine.drone import auto_squad, drone_squad
from engine.models import (
    Instrument,
    InstrumentWeek,
    Order,
    PlayerWeek,
    Swap,
    WeekInput,
    WeekResult,
)
from engine.orders import resolve_orders
from engine.ranking import WeekRecord, ammo_delta, campaign_standings, competition_ranks
from engine.returns import weekly_return
from engine.scoring import score_week
from jobs import dispatch
from jobs.db import Connection, RetryLater, run_league_once
from jobs.market_jobs import reference_prices, week_confirmed

log = logging.getLogger(__name__)

THURSDAY_DISPATCH_LOCAL_TIME = "09:10:00"
MONDAY_DISPATCH_MIC = "XPAR"  # "Monday, EU open + 10 min"


# --- loading ---------------------------------------------------------------------------------
@dataclass
class Member:
    member_id: str
    pseudo: str
    commander: str | None
    is_drone: bool


@dataclass
class WeekData:
    league_id: str
    week: date
    row: dict[str, Any]
    members: dict[str, Member]
    units: dict[str, dict[str, int]]
    swaps: dict[str, list[Swap]]
    orders: list[Order]
    allies: dict[str, str | None]
    points_before: dict[str, float]
    instruments: dict[int, Instrument]
    zone: set[int]
    coefs: dict[int, tuple[float, float | None]] = field(default_factory=dict)

    @property
    def humans(self) -> list[Member]:
        return [m for m in self.members.values() if not m.is_drone]


def _load(conn: Connection, league_id: str, week: date) -> WeekData:
    row = conn.execute(
        "select * from public.weeks where league_id = %s and week = %s", (league_id, week)
    ).fetchone()
    assert row is not None
    members = {
        str(r["member_id"]): Member(str(r["member_id"]), r["pseudo"], r["commander"], r["is_drone"])
        for r in conn.execute(
            "select member_id, pseudo, commander::text as commander, is_drone "
            "from public.league_members where league_id = %s",
            (league_id,),
        ).fetchall()
    }
    units: dict[str, dict[str, int]] = {}
    for r in conn.execute(
        "select member_id, slot::text as slot, instrument_id from public.squad_units "
        "where league_id = %s and week = %s",
        (league_id, week),
    ).fetchall():
        units.setdefault(str(r["member_id"]), {})[r["slot"]] = r["instrument_id"]
    swaps: dict[str, list[Swap]] = {}
    for r in conn.execute(
        "select member_id, slot::text as slot, reserve_slot::text as reserve_slot "
        "from public.swaps where league_id = %s and week = %s order by created_at",
        (league_id, week),
    ).fetchall():
        swaps.setdefault(str(r["member_id"]), []).append(Swap(r["slot"], r["reserve_slot"]))
    orders = [
        Order(
            id=str(r["id"]),
            member_id=str(r["member_id"]),
            type=r["type"],
            created_at=r["created_at"],
            window=r["order_window"],
            target_member_id=str(r["target_member_id"]) if r["target_member_id"] else None,
            target_slot=r["target_slot"],
        )
        for r in conn.execute(
            "select id, member_id, type::text as type, created_at, "
            "order_window::text as order_window, target_member_id, target_slot::text as "
            "target_slot from public.orders where league_id = %s and week = %s "
            "and status <> 'rejected'",
            (league_id, week),
        ).fetchall()
    ]
    allies: dict[str, str | None] = {m: None for m in members}
    for r in conn.execute(
        "select proposer_member_id as a, partner_member_id as b from public.pacts "
        "where league_id = %s and week = %s and status = 'active'",
        (league_id, week),
    ).fetchall():
        allies[str(r["a"])], allies[str(r["b"])] = str(r["b"]), str(r["a"])
    points_before = {m: 0.0 for m in members}
    for r in conn.execute(
        "select member_id, coalesce(sum(campaign_points), 0) as points from public.scores_final "
        "where league_id = %s and week < %s group by member_id",
        (league_id, week),
    ).fetchall():
        points_before[str(r["member_id"])] = float(r["points"])
    instruments = {
        r["id"]: Instrument(r["id"], r["region"])
        for r in conn.execute(
            "select id, region::text as region from public.instruments"
        ).fetchall()
    }
    zone: set[int] = set()
    coefs: dict[int, tuple[float, float | None]] = {}
    for r in conn.execute(
        "select instrument_id, coef, prev_week_return, in_conflict_zone "
        "from public.instrument_weeks where week = %s",
        (week,),
    ).fetchall():
        coefs[r["instrument_id"]] = (
            float(r["coef"]) if r["coef"] is not None else 1.0,
            float(r["prev_week_return"]) if r["prev_week_return"] is not None else None,
        )
        if r["in_conflict_zone"]:
            zone.add(r["instrument_id"])
    return WeekData(
        str(league_id),
        week,
        row,
        members,
        units,
        swaps,
        orders,
        allies,
        points_before,
        instruments,
        zone,
        coefs,
    )


def _week_input(data: WeekData, prices: Mapping[int, InstrumentWeek]) -> WeekInput:
    players = tuple(
        PlayerWeek(
            member_id=m.member_id,
            commander=None if m.is_drone else m.commander,
            units=data.units.get(m.member_id, {}),
            swaps=tuple(data.swaps.get(m.member_id, [])),
            is_drone=m.is_drone,
            campaign_points_before=data.points_before[m.member_id],
            ally_member_id=data.allies.get(m.member_id),
        )
        for m in data.members.values()
        if data.units.get(m.member_id)
    )
    return WeekInput(
        players=players,
        instruments=prices,
        orders=tuple(data.orders),
        is_final=bool(data.row["is_final"]),
    )


def _final_prices(conn: Connection, data: WeekData) -> dict[int, InstrumentWeek]:
    refs = reference_prices(conn, data.week)
    prices = {}
    for inst_id, inst in data.instruments.items():
        ref = refs.get(inst_id, {})
        coef, prev = data.coefs.get(inst_id, (1.0, None))
        prices[inst_id] = InstrumentWeek(
            inst_id,
            inst.region,
            ref.get("p0"),
            ref.get("p_mid"),
            ref.get("p_end"),
            d1=ref.get("d1", 0.0),
            d2=ref.get("d2", 0.0),
            coef=coef,
            prev_week_return=prev,
        )
    return prices


def _live_prices(conn: Connection, data: WeekData, now: datetime) -> dict[int, InstrumentWeek]:
    """Provisional prices: reference prices captured so far, the latest live quote as the
    end of the open segment."""
    refs = reference_prices(conn, data.week)
    latest = {
        r["instrument_id"]: float(r["price"])
        for r in conn.execute(
            "select distinct on (instrument_id) instrument_id, price from public.prices_live "
            "where ts <= %s and ts >= %s order by instrument_id, ts desc",
            (now, data.row["lock_at"]),
        ).fetchall()
    }
    prices = {}
    for inst_id, inst in data.instruments.items():
        ref = refs.get(inst_id, {})
        coef, prev = data.coefs.get(inst_id, (1.0, None))
        live = latest.get(inst_id)
        if "p_mid" in ref:
            p_mid, p_end = ref["p_mid"], ref.get("p_end", live)
        else:
            p_mid, p_end = live, None
        prices[inst_id] = InstrumentWeek(
            inst_id, inst.region, ref.get("p0"), p_mid, p_end, coef=coef, prev_week_return=prev
        )
    return prices


# --- transitions -----------------------------------------------------------------------------
def _open_briefing(conn: Connection, data: WeekData) -> None:
    ts = phase_timestamps(data.week)
    conn.execute(
        "update public.weeks set lock_at = %s, resupply_opens_at = %s, resupply_closes_at = %s, "
        "debrief_at = %s, phase = 'briefing', phase_changed_at = now() "
        "where league_id = %s and week = %s",
        (
            ts.lock_at,
            ts.resupply_opens_at,
            ts.resupply_closes_at,
            ts.debrief_at,
            data.league_id,
            data.week,
        ),
    )
    history = [
        WeekRecord(str(r["member_id"]), float(r["campaign_points"]), r["rank"] or 0, r["pf_total"])
        for r in conn.execute(
            "select f.member_id, f.campaign_points, f.rank, f.pf_total from public.scores_final f "
            "join public.league_members m on m.member_id = f.member_id "
            "where f.league_id = %s and f.week < %s and not m.is_drone",
            (data.league_id, data.week),
        ).fetchall()
    ]
    humans = [m.member_id for m in data.humans]
    ranks = {s.member_id: s.rank for s in campaign_standings(humans, history)}
    for member in data.humans:
        balance = conn.execute(
            "select coalesce(sum(delta), 0)::int as b from public.ammo_ledger where member_id = %s",
            (member.member_id,),
        ).fetchone()
        delta = ammo_delta(
            member.commander,
            balance["b"] if balance else 0,
            week_number=data.row["number"],
            campaign_rank=ranks[member.member_id],
            humans=len(humans),
        )
        if delta:
            conn.execute(
                "insert into public.ammo_ledger (league_id, member_id, week, delta, reason) "
                "values (%s, %s, %s, %s, 'income')",
                (data.league_id, member.member_id, data.week, delta),
            )


def _insert_squad(
    conn: Connection, data: WeekData, member_id: str, squad: Mapping[str, int], auto: bool
) -> None:
    conn.execute(
        "insert into public.squads (league_id, week, member_id, locked, auto) "
        "values (%s, %s, %s, true, %s) on conflict (league_id, week, member_id) "
        "do update set locked = true, auto = excluded.auto",
        (data.league_id, data.week, member_id, auto),
    )
    conn.execute(
        "delete from public.squad_units where league_id = %s and week = %s and member_id = %s",
        (data.league_id, data.week, member_id),
    )
    for slot, inst in squad.items():
        front = slot in config.FRONT_SLOTS
        conn.execute(
            "insert into public.squad_units (league_id, week, member_id, slot, instrument_id, "
            "active_s1, active_s2) values (%s, %s, %s, %s, %s, %s, %s)",
            (data.league_id, data.week, member_id, slot, inst, front, front),
        )
    data.units[member_id] = dict(squad)


def _resolve(conn: Connection, data: WeekData, window: str, now: datetime) -> None:
    resolution = resolve_orders(data.orders, data.allies)
    for order in data.orders:
        status = resolution.status.get(order.id, "pending")
        resolved = order.window == window or (order.window == "briefing" and window == "resupply")
        conn.execute(
            "update public.orders set status = %s, resolved_at = coalesce(resolved_at, %s) "
            "where id = %s and type <> 'intel'",
            (status, now if resolved and status != "pending" else None, order.id),
        )


def _lock(conn: Connection, data: WeekData, now: datetime) -> None:
    if not data.zone:
        raise RetryLater("no Conflict Zone for this week yet")
    previous_week = data.week - timedelta(days=7)
    for member in data.members.values():
        if member.is_drone:
            squad = drone_squad(data.league_id, data.week.isoformat(), data.instruments, data.zone)
            _insert_squad(conn, data, member.member_id, squad, auto=True)
            continue
        if data.units.get(member.member_id):
            conn.execute(
                "update public.squads set locked = true where league_id = %s and week = %s "
                "and member_id = %s",
                (data.league_id, data.week, member.member_id),
            )
            continue
        previous: dict[str, int] = {}
        for r in conn.execute(
            "select slot::text as slot, instrument_id from public.squad_units "
            "where league_id = %s and week = %s and member_id = %s",
            (data.league_id, previous_week, member.member_id),
        ).fetchall():
            previous[r["slot"]] = r["instrument_id"]
        squad = auto_squad(
            member.member_id,
            data.week.isoformat(),
            member.commander,
            previous or None,
            data.instruments,
            data.zone,
        )
        _insert_squad(conn, data, member.member_id, squad, auto=True)
    _resolve(conn, data, "briefing", now)
    _set_phase(conn, data, "s1_live")


def _close_resupply(conn: Connection, data: WeekData, now: datetime) -> None:
    _resolve(conn, data, "resupply", now)
    for member_id, swaps in data.swaps.items():
        for swap in swaps:
            conn.execute(
                "update public.squad_units set active_s2 = false where league_id = %s "
                "and week = %s and member_id = %s and slot = %s",
                (data.league_id, data.week, member_id, swap.slot),
            )
            conn.execute(
                "update public.squad_units set active_s2 = true where league_id = %s "
                "and week = %s and member_id = %s and slot = %s",
                (data.league_id, data.week, member_id, swap.reserve_slot),
            )
    _set_phase(conn, data, "s2_live")


def _set_phase(conn: Connection, data: WeekData, phase: str) -> None:
    conn.execute(
        "update public.weeks set phase = %s, phase_changed_at = now() "
        "where league_id = %s and week = %s",
        (phase, data.league_id, data.week),
    )


def _jammed(conn: Connection, data: WeekData) -> set[str]:
    return {
        str(r["target_member_id"])
        for r in conn.execute(
            "select target_member_id from public.orders where league_id = %s and week = %s "
            "and type = 'jamming' and status = 'applied'",
            (data.league_id, data.week),
        ).fetchall()
    }


def live_scores(conn: Connection, data: WeekData, now: datetime) -> WeekResult | None:
    """Writes the private live scores and the masked public table (GAME_RULES §6)."""
    week_input = _week_input(data, _live_prices(conn, data, now))
    if not week_input.players:
        return None
    result = score_week(week_input)
    jammed = _jammed(conn, data)
    shadows = {m.member_id for m in data.humans if m.commander == "shadow"}
    visible = {
        m: r.pf_total
        for m, r in result.players.items()
        if not r.is_drone and m not in jammed and m not in shadows
    }
    ranks = competition_ranks(visible)
    with conn.transaction():
        for member_id, res in result.players.items():
            units = {s: d["pf"] for s, d in res.breakdown["slots"].items()}  # type: ignore[attr-defined]
            conn.execute(
                "insert into public.scores_live (league_id, week, member_id, pf_live, units, "
                "updated_at) values (%s, %s, %s, %s, %s, %s) on conflict (league_id, week, "
                "member_id) do update set pf_live = excluded.pf_live, units = excluded.units, "
                "updated_at = excluded.updated_at",
                (data.league_id, data.week, member_id, res.pf_total, Jsonb(units), now),
            )
            if member_id in shadows:
                conn.execute(
                    "delete from public.scores_live_public where league_id = %s and week = %s "
                    "and member_id = %s",
                    (data.league_id, data.week, member_id),
                )
                continue
            hidden = member_id in jammed
            conn.execute(
                "insert into public.scores_live_public (league_id, week, member_id, pf_live, "
                "rank_live, jammed, units, updated_at) values (%s, %s, %s, %s, %s, %s, %s, %s) "
                "on conflict (league_id, week, member_id) do update set pf_live = "
                "excluded.pf_live, rank_live = excluded.rank_live, jammed = excluded.jammed, "
                "units = excluded.units, updated_at = excluded.updated_at",
                (
                    data.league_id,
                    data.week,
                    member_id,
                    None if hidden else res.pf_total,
                    None if hidden or res.is_drone else ranks.get(member_id),
                    hidden,
                    Jsonb({} if hidden else units),
                    now,
                ),
            )
    return result


def _event(conn: Connection, data: WeekData, item: dispatch.Dispatch, now: datetime) -> None:
    conn.execute(
        "insert into public.events (league_id, week, ts, kind, template_key, vars, variant) "
        "values (%s, %s, %s, 'dispatch', %s, %s, %s)",
        (data.league_id, data.week, now, item.template_key, Jsonb(item.vars), item.variant),
    )


def _monday_dispatch(conn: Connection, data: WeekData, now: datetime) -> None:
    result = live_scores(conn, data, now)
    if result is None:
        raise RetryLater("no squads yet")
    prices = _live_prices(conn, data, now)
    # Opening gap and early move: latest quote against last Friday's close.
    previous = reference_prices(conn, data.week - timedelta(days=7))
    moves = {
        i: (p.p_mid / previous[i]["p_end"] - 1) * 100
        for i, p in prices.items()
        if p.p_mid and previous.get(i, {}).get("p_end")
    }
    tickers = {
        r["id"]: r["ticker"]
        for r in conn.execute("select id, ticker from public.instruments").fetchall()
    }
    mover = max(moves, key=lambda i: abs(moves[i])) if moves else None
    jammed = _jammed(conn, data)
    players = [
        dispatch.LivePlayer(
            m.pseudo,
            result.players[m.member_id].pf_total if m.member_id in result.players else None,
            hidden=m.commander == "shadow" or m.member_id in jammed,
        )
        for m in data.humans
    ]
    _event(
        conn,
        data,
        dispatch.monday(
            data.league_id,
            data.week.isoformat(),
            players,
            tickers.get(mover) if mover else None,
            moves.get(mover) if mover else None,
        ),
        now,
    )


def _thursday_dispatch(conn: Connection, data: WeekData, now: datetime) -> None:
    shadows = {m.member_id for m in data.humans if m.commander == "shadow"}
    counts = conn.execute(
        "select "
        "count(*) filter (where type in ('orbital_strike','pillage','blockade','jamming') "
        "and status = 'applied') as attacks, "
        "count(*) filter (where status = 'blocked') as blocked "
        "from public.orders where league_id = %s and week = %s",
        (data.league_id, data.week),
    ).fetchone()
    swaps = sum(len(s) for m, s in data.swaps.items() if m not in shadows)
    pacts = sum(1 for a, b in data.allies.items() if b) // 2
    _event(
        conn,
        data,
        dispatch.thursday(
            data.league_id,
            data.week.isoformat(),
            swaps=swaps,
            attacks=counts["attacks"] if counts else 0,
            blocked=counts["blocked"] if counts else 0,
            pacts=pacts,
        ),
        now,
    )


def _debrief(conn: Connection, data: WeekData, now: datetime) -> None:
    if not week_confirmed(conn, data.week):
        raise RetryLater("reference prices not confirmed yet")
    prices = _final_prices(conn, data)
    result = score_week(_week_input(data, prices))
    for order_id, status in result.orders.status.items():
        conn.execute(
            "update public.orders set status = %s, resolved_at = coalesce(resolved_at, %s) "
            "where id = %s and type <> 'intel'",
            (status, now if status != "pending" else None, order_id),
        )
    for member_id, res in result.players.items():
        conn.execute(
            "insert into public.scores_final (league_id, week, member_id, pf_total, pf_picking, "
            "breakdown, rank, campaign_points) values (%s, %s, %s, %s, %s, %s, %s, %s) "
            "on conflict (league_id, week, member_id) do update set pf_total = "
            "excluded.pf_total, pf_picking = excluded.pf_picking, breakdown = "
            "excluded.breakdown, rank = excluded.rank, campaign_points = excluded.campaign_points",
            (
                data.league_id,
                data.week,
                member_id,
                res.pf_total,
                res.pf_picking,
                Jsonb(res.breakdown),
                res.rank,
                res.campaign_points,
            ),
        )
        for code in res.badges:
            conn.execute(
                "insert into public.badges (league_id, week, member_id, code) "
                "values (%s, %s, %s, %s) on conflict do nothing",
                (data.league_id, data.week, member_id, code),
            )
    _event(conn, data, _debrief_dispatch(conn, data, result, prices), now)
    _set_phase(conn, data, "debrief")
    if data.row["number"] >= _campaign_weeks(conn, data.league_id):
        conn.execute(
            "update public.leagues set status = 'finished' where id = %s", (data.league_id,)
        )
        return
    next_week = data.week + timedelta(days=7)
    ts = phase_timestamps(next_week)
    number = data.row["number"] + 1
    conn.execute(
        "insert into public.weeks (league_id, week, number, phase, is_final, lock_at, "
        "resupply_opens_at, resupply_closes_at, debrief_at) values (%s, %s, %s, 'briefing', "
        "%s, %s, %s, %s, %s) on conflict do nothing",
        (
            data.league_id,
            next_week,
            number,
            number == _campaign_weeks(conn, data.league_id),
            ts.lock_at,
            ts.resupply_opens_at,
            ts.resupply_closes_at,
            ts.debrief_at,
        ),
    )


def _campaign_weeks(conn: Connection, league_id: str) -> int:
    row = conn.execute(
        "select campaign_weeks from public.leagues where id = %s", (league_id,)
    ).fetchone()
    return int(row["campaign_weeks"]) if row else 0


def _debrief_dispatch(
    conn: Connection, data: WeekData, result: WeekResult, prices: Mapping[int, InstrumentWeek]
) -> dispatch.Dispatch:
    humans = [r for r in result.players.values() if not r.is_drone]
    winner = min(humans, key=lambda r: (r.rank or 99, -r.pf_total))
    tickers = {
        r["id"]: r["ticker"]
        for r in conn.execute("select id, ticker from public.instruments").fetchall()
    }
    held = {i for r in humans for i in data.units.get(r.member_id, {}).values()}
    returns = {i: weekly_return(prices[i]) for i in held if i in prices}
    ranked = sorted((r, i) for i, r in returns.items() if r is not None)
    best, worst = (ranked[-1][1], ranked[0][1]) if ranked else (None, None)
    drone = next((r for r in result.players.values() if r.is_drone), None)
    return dispatch.debrief(
        data.league_id,
        data.week.isoformat(),
        winner=data.members[winner.member_id].pseudo,
        pf=winner.pf_total,
        best=tickers.get(best, "-") if best else "-",
        best_move=round(returns[best] or 0, 1) if best else 0,
        worst=tickers.get(worst, "-") if worst else "-",
        worst_move=round(returns[worst] or 0, 1) if worst else 0,
        drone_pf=drone.pf_total if drone else 0,
        rusty=sum(1 for r in humans if "rusty" in r.badges),
    )


# --- the tick --------------------------------------------------------------------------------
def league_tick(
    conn: Connection, now: datetime, league_ids: Sequence[str] | None = None
) -> list[str]:
    """Runs every due league transition (only for `league_ids` when given, e.g. a replay)."""
    done: list[str] = []
    leagues = conn.execute("select id from public.leagues where status = 'active'").fetchall()
    if league_ids is not None:
        leagues = [row for row in leagues if str(row["id"]) in set(league_ids)]
    for league in leagues:
        league_id = str(league["id"])
        row = conn.execute(
            "select week from public.weeks where league_id = %s order by week desc limit 1",
            (league_id,),
        ).fetchone()
        if row is None:
            continue
        week = row["week"]

        def step(name: str, due: bool, work: Any, lid: str = league_id, wk: date = week) -> None:
            if due and run_league_once(
                conn, lid, wk, name, lambda: work(conn, _load(conn, lid, wk), now)
            ):
                done.append(f"{lid[:8]} {wk} {name}")

        step("open_briefing", True, lambda c, d, n: _open_briefing(c, d))
        data = _load(conn, league_id, week)
        ts = data.row
        step("lock", now >= ts["lock_at"], _lock)
        monday_open = first_open(MONDAY_DISPATCH_MIC, week)
        if monday_open is not None:
            step(
                "dispatch_monday",
                now >= monday_open + timedelta(minutes=config.PRICE_CAPTURE_DELAY_MIN)
                and _done(conn, league_id, week, "lock"),
                _monday_dispatch,
            )
        step(
            "open_resupply",
            ts["resupply_opens_at"] is not None and now >= ts["resupply_opens_at"],
            lambda c, d, n: _set_phase(c, d, "resupply"),
        )
        step("close_resupply", now >= ts["resupply_closes_at"], _close_resupply)
        thursday = local_instant(week + timedelta(days=3), THURSDAY_DISPATCH_LOCAL_TIME)
        step(
            "dispatch_thursday",
            now >= thursday and _done(conn, league_id, week, "close_resupply"),
            _thursday_dispatch,
        )
        debrief_due = ts["debrief_at"] is not None and now >= ts["debrief_at"]
        step("debrief", debrief_due, _debrief)
        if _done(conn, league_id, week, "lock") and not _done(conn, league_id, week, "debrief"):
            live_scores(conn, _load(conn, league_id, week), now)
            done.append(f"{league_id[:8]} {week} live_scores")
    return done


def _done(conn: Connection, league_id: str, week: date, transition: str) -> bool:
    return (
        conn.execute(
            "select 1 from public.job_runs where league_id = %s and week = %s and transition = %s",
            (league_id, week, transition),
        ).fetchone()
        is not None
    )
