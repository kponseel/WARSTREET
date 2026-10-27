"""Monte Carlo balance check: campaign win rate per commander.

    python -m engine.simulate --players 4 --weeks 8 --runs 2000 [--seed 1]

Model (a balance tool, not a market forecast):
- 100 instruments (50 EU, 50 US) with a fixed weekly volatility each; coef from engine rules.
- Weekly returns: Student t (4 degrees of freedom), correlation 0.4 with one market factor,
  split into S1 (3/5 of the variance) and S2 (2/5).
- Drafts follow a popularity bias (a few stocks are picked often), so Elite unit overlaps
  are realistic. Squads are always valid. The Drone drafts uniformly.
- A simple random policy plays orders (respecting costs, Bounty, attack cap, Berserker,
  Blockade) and swaps a front unit that lost more than 3 % in S1. No pacts.
- Each player gets a random commander (duplicates allowed); a campaign win is shared
  between tied winners. Fair share = 1 / players.
"""

from __future__ import annotations

import argparse
import math
import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from engine import config
from engine.conflict_zone import coefficient
from engine.drone import random_squad
from engine.models import Instrument, InstrumentWeek, Order, PlayerWeek, Swap, WeekInput
from engine.orders import is_attack
from engine.ranking import WeekRecord, ammo_delta, bounty_member, campaign_standings, order_cost
from engine.scoring import score_week
from engine.squads import front_errors, max_swaps, reserve_size

DF = 4  # Student t degrees of freedom
MARKET_CORRELATION = 0.4
S1_SHARE = 3 / 5
VOLATILITIES = (2.0, 3.0, 4.0, 5.0, 7.0, 10.0)
SWAP_TRIGGER = -3.0  # % S1 loss that makes the policy swap a unit
T0 = datetime(2026, 1, 5, tzinfo=UTC)


def _student(rng: random.Random) -> float:
    """Standard Student t draw scaled to unit variance."""
    chi2 = rng.gammavariate(DF / 2, 2)
    return rng.gauss(0, 1) / math.sqrt(chi2 / DF) / math.sqrt(DF / (DF - 2))


@dataclass
class Universe:
    instruments: dict[int, Instrument]
    vol: dict[int, float]
    weight: dict[int, float]

    @classmethod
    def build(cls, rng: random.Random) -> Universe:
        ids = list(range(1, 101))
        instruments = {i: Instrument(i, "EU" if i <= 50 else "US") for i in ids}
        vol = {i: rng.choice(VOLATILITIES) for i in ids}
        ranks = ids[:]
        rng.shuffle(ranks)
        weight = {i: 1 / (rank**0.8) for rank, i in enumerate(ranks, start=1)}
        return cls(instruments, vol, weight)

    def week_returns(self, rng: random.Random) -> dict[int, tuple[float, float]]:
        returns = {}
        markets = (_student(rng), _student(rng))
        for i, sigma in self.vol.items():
            pair = []
            for market, share in zip(markets, (S1_SHARE, 1 - S1_SHARE), strict=True):
                shock = math.sqrt(MARKET_CORRELATION) * market + math.sqrt(
                    1 - MARKET_CORRELATION
                ) * _student(rng)
                pair.append(max(-60.0, sigma * math.sqrt(share) * shock))
            returns[i] = (pair[0], pair[1])
        return returns


def _weighted_pick(rng: random.Random, candidates: Sequence[int], weight: dict[int, float]) -> int:
    return rng.choices(list(candidates), weights=[weight[c] for c in candidates])[0]


def draft(
    rng: random.Random, universe: Universe, zone: set[int], commander: str | None
) -> dict[str, int]:
    """A valid squad drafted with the popularity bias."""
    inst, used = universe.instruments, set()

    def pick(region: str | None, pool: Sequence[int] | None = None) -> int:
        candidates = [
            i
            for i in (pool if pool is not None else inst)
            if i not in used and (region is None or inst[i].region == region)
        ]
        choice = _weighted_pick(rng, candidates, universe.weight)
        used.add(choice)
        return choice

    squad = {"priority_target": pick(None, sorted(zone))}
    champion_region = rng.choice(("EU", "US"))
    squad["champion"] = pick(champion_region)
    squad["veteran"] = pick("US" if champion_region == "EU" else "EU")
    for slot in ("marksman", "saboteur"):
        counts = {r: sum(1 for i in squad.values() if inst[i].region == r) for r in ("EU", "US")}
        short = [r for r in counts if counts[r] < config.FRONT_MIN_PER_REGION]
        squad[slot] = pick(short[0] if short else None)
    for index, slot in enumerate(config.RESERVE_SLOTS[: reserve_size(commander)]):
        squad[slot] = pick(("EU", "US")[index] if index < 2 else None)
    return squad


@dataclass
class Player:
    member_id: str
    commander: str
    ammo: int = 0
    history: list[WeekRecord] = field(default_factory=list)


def _choose_orders(
    rng: random.Random,
    players: list[Player],
    squads: dict[str, dict[str, int]],
    s1: dict[int, float],
    points: dict[str, float],
    week_start: datetime,
) -> list[Order]:
    """A simple random policy for briefing and resupply orders."""
    orders: list[Order] = []
    attacks: dict[str, int] = defaultdict(int)
    blockaded: set[str] = set()
    leader = bounty_member(points)
    minute = 0

    def play(player: Player, order_type: str, window: str, **target: str | None) -> None:
        nonlocal minute
        victim = target.get("target_member_id")
        cost = order_cost(order_type, victim is not None and victim == leader)
        if player.ammo < cost or (victim and attacks[victim] >= config.ATTACK_CAP_PER_WEEK):
            return
        if player.commander == "berserker" and order_type in config.BERSERKER_FORBIDDEN_ORDERS:
            return
        player.ammo -= cost
        minute += 1
        offset = timedelta(minutes=minute) + (
            timedelta(days=4) if window == "resupply" else timedelta()
        )
        orders.append(
            Order(
                id=f"o{minute}",
                member_id=player.member_id,
                type=order_type,
                created_at=week_start + offset,
                window=window,  # type: ignore[arg-type]
                target_member_id=victim,
                target_slot=target.get("target_slot"),
            )
        )
        if victim and is_attack(order_type):
            attacks[victim] += 1
            if order_type == "blockade":
                blockaded.add(victim)

    for player in rng.sample(players, len(players)):
        others = [p.member_id for p in players if p is not player]
        roll = rng.random()
        if roll < 0.25:
            play(player, "force_field", "briefing")
        elif roll < 0.45:
            play(player, "blockade", "briefing", target_member_id=rng.choice(others))
        elif roll < 0.6:
            play(player, "jamming", "briefing", target_member_id=rng.choice(others))
    for player in rng.sample(players, len(players)):
        if player.member_id in blockaded:
            continue
        others = [p.member_id for p in players if p is not player]
        squad = squads[player.member_id]
        roll = rng.random()
        if roll < 0.3:
            play(player, "pillage", "resupply", target_member_id=rng.choice(others))
        elif roll < 0.5:
            play(
                player,
                "orbital_strike",
                "resupply",
                target_member_id=rng.choice(others),
                target_slot="champion",
            )
        elif roll < 0.6 and s1[squad["marksman"]] < 0:
            play(player, "reversal", "resupply")
        elif roll < 0.7:
            worst = min(config.FRONT_SLOTS, key=lambda s: s1[squad[s]])
            play(player, "tactical_retreat", "resupply", target_slot=worst)
        elif roll < 0.8:
            best = max(("veteran", "marksman", "priority_target"), key=lambda s: s1[squad[s]])
            play(player, "field_promotion", "resupply", target_slot=best)
    return orders


def _swaps(
    squad: dict[str, int],
    commander: str,
    s1: dict[int, float],
    universe: Universe,
    zone: set[int],
) -> tuple[Swap, ...]:
    swaps: list[Swap] = []
    front = {s: squad[s] for s in config.FRONT_SLOTS}
    reserves = [s for s in config.RESERVE_SLOTS if s in squad]
    for slot in sorted(config.FRONT_SLOTS, key=lambda s: s1[squad[s]]):
        if len(swaps) >= max_swaps(commander) or s1[squad[slot]] >= SWAP_TRIGGER:
            break
        for reserve in reserves:
            if any(sw.reserve_slot == reserve for sw in swaps):
                continue
            candidate = {**front, slot: squad[reserve]}
            if not front_errors(candidate, universe.instruments, zone):
                swaps.append(Swap(slot, reserve))
                front = candidate
                break
    return tuple(swaps)


@dataclass
class Totals:
    appearances: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    wins: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    elite_pf: int = 0
    rusty: int = 0
    player_weeks: int = 0


def simulate_campaign(rng: random.Random, players_count: int, weeks: int, totals: Totals) -> None:
    universe = Universe.build(rng)
    players = [Player(f"P{i}", rng.choice(config.COMMANDERS)) for i in range(players_count)]
    previous: dict[int, float] = {}
    for week_number in range(1, weeks + 1):
        standings = campaign_standings(
            [p.member_id for p in players], [r for p in players for r in p.history]
        )
        rank = {s.member_id: s.rank for s in standings}
        points = {s.member_id: s.campaign_points for s in standings}
        for p in players:
            p.ammo += ammo_delta(
                p.commander,
                p.ammo,
                week_number=week_number,
                campaign_rank=rank[p.member_id],
                humans=players_count,
            )
        zone = set(rng.sample(sorted(universe.instruments), config.CONFLICT_ZONE_SIZE))
        returns = universe.week_returns(rng)
        s1 = {i: r[0] for i, r in returns.items()}
        squads = {p.member_id: draft(rng, universe, zone, p.commander) for p in players}
        week_start = T0 + timedelta(weeks=week_number)
        orders = _choose_orders(rng, players, squads, s1, points, week_start)
        blockaded = {o.target_member_id for o in orders if o.type == "blockade"}
        players_week = [
            PlayerWeek(
                member_id=p.member_id,
                commander=p.commander,
                units=squads[p.member_id],
                swaps=()
                if p.member_id in blockaded
                else _swaps(squads[p.member_id], p.commander, s1, universe, zone),
                campaign_points_before=points[p.member_id],
            )
            for p in players
        ]
        drone = PlayerWeek(
            "Drone", None, random_squad(rng, universe.instruments, zone), is_drone=True
        )
        instruments = {}
        for i, (r1, r2) in returns.items():
            p_mid = 100 * (1 + r1 / 100)
            instruments[i] = InstrumentWeek(
                i,
                universe.instruments[i].region,
                p0=100.0,
                p_mid=p_mid,
                p_end=p_mid * (1 + r2 / 100),
                coef=coefficient(universe.vol[i]),
                prev_week_return=previous.get(i),
            )
        result = score_week(
            WeekInput(
                players=(*players_week, drone),
                instruments=instruments,
                orders=tuple(orders),
                is_final=week_number == weeks,
            )
        )
        previous = {
            i: ((1 + r1 / 100) * (1 + r2 / 100) - 1) * 100 for i, (r1, r2) in returns.items()
        }
        for p in players:
            res = result.players[p.member_id]
            p.history.append(
                WeekRecord(p.member_id, res.campaign_points, res.rank or 0, res.pf_total)
            )
            totals.elite_pf += int(res.breakdown["elite"]["pf"])  # type: ignore[index]
            totals.rusty += "rusty" in res.badges
            totals.player_weeks += 1
    final = campaign_standings(
        [p.member_id for p in players], [r for p in players for r in p.history]
    )
    winners = [s.member_id for s in final if s.rank == 1]
    for p in players:
        totals.appearances[p.commander] += 1
        if p.member_id in winners:
            totals.wins[p.commander] += 1 / len(winners)


def run(players: int, weeks: int, runs: int, seed: int) -> str:
    rng = random.Random(seed)
    totals = Totals()
    for _ in range(runs):
        simulate_campaign(rng, players, weeks, totals)
    fair = 1 / players
    lines = [
        f"players={players} weeks={weeks} runs={runs} seed={seed} fair share={fair:.1%}",
        f"{'commander':<14}{'games':>7}{'win rate':>10}{'vs fair':>9}",
    ]
    for commander in config.COMMANDERS:
        games = totals.appearances[commander]
        rate = totals.wins[commander] / games if games else 0.0
        ratio = rate / fair - 1
        flag = "  <-- outside ±30 %" if abs(ratio) > 0.30 else ""
        lines.append(f"{commander:<14}{games:>7}{rate:>10.1%}{ratio:>+9.0%}{flag}")
    lines.append(
        f"average Elite unit bonus per player-week: {totals.elite_pf / totals.player_weeks:.1f} PF"
    )
    lines.append(f"rusty badge frequency per player-week: {totals.rusty / totals.player_weeks:.1%}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--players", type=int, default=4, choices=sorted(config.CAMPAIGN_POINTS))
    parser.add_argument("--weeks", type=int, default=config.CAMPAIGN_WEEKS_DEFAULT)
    parser.add_argument("--runs", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args(argv)
    print(run(args.players, args.weeks, args.runs, args.seed))


if __name__ == "__main__":
    main()
