"""Database test harness.

Environment:
- WARSTREET_TEST_DB_URL: admin connection string (e.g. postgresql://postgres@localhost:54322/postgres).
  Without it the database tests are skipped, unless WARSTREET_REQUIRE_DB=1 (then they fail).
- WARSTREET_TEST_DB_PREPARED=1: test in the database of the URL itself (the Supabase CLI's
  Postgres in CI, with the real auth schema and roles); migrations and seed are applied first
  if they are not there yet. Otherwise a fresh database is created next to it, the Supabase
  shim applied if needed, then every migration and the seed, and it is dropped at the end.

Every test runs in one transaction that is rolled back; RPC calls run in savepoints so a
rejected call does not abort the test.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg import errors
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = sorted((REPO_ROOT / "supabase" / "migrations").glob("*.sql"))
SHIM = REPO_ROOT / "supabase" / "tests" / "supabase_shim.sql"
SEED = REPO_ROOT / "supabase" / "seed.sql"

ADMIN_URL = os.environ.get("WARSTREET_TEST_DB_URL")
PREPARED = os.environ.get("WARSTREET_TEST_DB_PREPARED") == "1"
REQUIRE = os.environ.get("WARSTREET_REQUIRE_DB") == "1"

# Week used by the scenarios: Monday 2026-11-09 (Paris is UTC+1 in November).
WEEK = date(2026, 11, 9)
PREV_WEEK = date(2026, 11, 2)
T_BEFORE_START = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)  # Wednesday
T_BRIEFING = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)  # Saturday
LOCK_AT = datetime(2026, 11, 8, 22, 59, 59, tzinfo=UTC)  # Sunday 23:59:59 Paris
T_AFTER_LOCK = datetime(2026, 11, 9, 10, 0, tzinfo=UTC)
RESUPPLY_OPENS_AT = datetime(2026, 11, 11, 21, 5, tzinfo=UTC)
T_RESUPPLY = datetime(2026, 11, 11, 22, 0, tzinfo=UTC)
RESUPPLY_CLOSES_AT = datetime(2026, 11, 12, 7, 59, 59, tzinfo=UTC)  # Thursday 08:59:59 Paris
T_S2 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
DEBRIEF_AT = datetime(2026, 11, 13, 21, 30, tzinfo=UTC)
T_DEBRIEF = datetime(2026, 11, 13, 22, 0, tzinfo=UTC)

CONFLICT_ZONE = ("MC.PA", "SAP.DE", "AIR.PA", "TTE.PA", "AAPL", "MSFT", "NVDA", "KO")


class RpcError(Exception):
    def __init__(self, code: str, variables: dict[str, Any]) -> None:
        super().__init__(f"{code} {variables}")
        self.code = code
        self.vars = variables


def _apply(conn: psycopg.Connection[Any], path: Path) -> None:
    conn.execute(path.read_text(encoding="utf-8").encode())


def _migrate(conn: psycopg.Connection[Any]) -> None:
    has_auth = conn.execute("select to_regnamespace('auth') is not null").fetchone()
    if not (has_auth and has_auth[0]):
        _apply(conn, SHIM)
    for migration in MIGRATIONS:
        _apply(conn, migration)
    _apply(conn, SEED)


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    if not ADMIN_URL:
        if REQUIRE:
            pytest.fail("WARSTREET_TEST_DB_URL is required (WARSTREET_REQUIRE_DB=1)")
        pytest.skip("database tests need WARSTREET_TEST_DB_URL")
    if PREPARED:
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            migrated = conn.execute(
                "select to_regclass('public.game_config') is not null"
            ).fetchone()
            if not (migrated and migrated[0]):
                _migrate(conn)
        yield ADMIN_URL
        return
    name = f"warstreet_test_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        admin.execute(f'create database "{name}"'.encode())
    url = make_conninfo(ADMIN_URL, dbname=name)
    try:
        with psycopg.connect(url, autocommit=True) as conn:
            _migrate(conn)
        yield url
    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            admin.execute(f'drop database if exists "{name}" with (force)'.encode())


@dataclass
class Db:
    conn: psycopg.Connection[dict[str, Any]]
    _instrument_ids: dict[str, int] = field(default_factory=dict)

    # --- identity and clock ------------------------------------------------------------
    def admin(self) -> None:
        self.conn.execute("reset role")
        self.conn.execute("select set_config('request.jwt.claims', '', true)")
        self.conn.execute("select set_config('request.jwt.claim.sub', '', true)")

    def as_user(self, user_id: uuid.UUID | None) -> None:
        self.admin()
        self.conn.execute("set local role authenticated")
        if user_id is not None:
            claims = json.dumps({"sub": str(user_id), "role": "authenticated"})
            self.conn.execute("select set_config('request.jwt.claims', %s, true)", (claims,))
            self.conn.execute(
                "select set_config('request.jwt.claim.sub', %s, true)", (str(user_id),)
            )

    def as_anon(self) -> None:
        self.admin()
        self.conn.execute("set local role anon")

    def set_now(self, instant: datetime) -> None:
        self.conn.execute("select set_config('app.fake_now', %s, true)", (instant.isoformat(),))

    # --- data helpers (admin) ----------------------------------------------------------
    def create_user(self) -> uuid.UUID:
        self.admin()
        user_id = uuid.uuid4()
        self.conn.execute(
            "insert into auth.users (id, email) values (%s, %s)",
            (user_id, f"{user_id.hex[:12]}@example.test"),
        )
        return user_id

    def instrument(self, ticker: str) -> int:
        if ticker not in self._instrument_ids:
            self.admin()
            row = self.conn.execute(
                "select id from public.instruments where ticker = %s", (ticker,)
            ).fetchone()
            assert row is not None, ticker
            self._instrument_ids[ticker] = row["id"]
        return self._instrument_ids[ticker]

    def exec_admin(self, query: str, params: Any = None) -> None:
        self.admin()
        self.conn.execute(query.encode(), params)

    def fetch_admin(self, query: str, params: Any = None) -> list[dict[str, Any]]:
        self.admin()
        return self.conn.execute(query.encode(), params).fetchall()

    # --- calls as a user ---------------------------------------------------------------
    def rpc(self, user_id: uuid.UUID | None, function: str, **params: Any) -> Any:
        args = ", ".join(f"{name} => %({name})s" for name in params)
        values = {k: Jsonb(v) if isinstance(v, (dict, list)) else v for k, v in params.items()}
        self.as_user(user_id)
        try:
            with self.conn.transaction():
                row = self.conn.execute(
                    f"select public.{function}({args}) as result".encode(), values
                ).fetchone()
        except errors.RaiseException as exc:
            detail = exc.diag.message_detail
            raise RpcError(
                exc.diag.message_primary or "", json.loads(detail) if detail else {}
            ) from None
        finally:
            self.admin()
        return row["result"] if row else None

    def rpc_rows(
        self, user_id: uuid.UUID | None, function: str, **params: Any
    ) -> list[dict[str, Any]]:
        """Calls a set-returning RPC (`select * from public.fn(...)`) as a user."""
        args = ", ".join(f"{name} => %({name})s" for name in params)
        self.as_user(user_id)
        try:
            with self.conn.transaction():
                return self.conn.execute(
                    f"select * from public.{function}({args})".encode(), params
                ).fetchall()
        except errors.RaiseException as exc:
            detail = exc.diag.message_detail
            raise RpcError(
                exc.diag.message_primary or "", json.loads(detail) if detail else {}
            ) from None
        finally:
            self.admin()

    def rpc_error(self, user_id: uuid.UUID | None, function: str, **params: Any) -> RpcError:
        with pytest.raises(RpcError) as info:
            self.rpc(user_id, function, **params)
        return info.value

    def select(
        self, user_id: uuid.UUID | None, query: str, params: Any = None
    ) -> list[dict[str, Any]]:
        self.as_user(user_id)
        try:
            with self.conn.transaction():
                return self.conn.execute(query.encode(), params).fetchall()
        finally:
            self.admin()


@pytest.fixture
def db(database_url: str) -> Iterator[Db]:
    conn = psycopg.connect(database_url, row_factory=dict_row)
    try:
        yield Db(conn)
    finally:
        conn.rollback()
        conn.close()


# --- scenario ------------------------------------------------------------------------------
VALID_SQUAD = {
    "champion": "AAPL",  # US
    "veteran": "MC.PA",  # EU
    "marksman": "MSFT",  # US
    "saboteur": "SAP.DE",  # EU
    "priority_target": "NVDA",  # US, in the Conflict Zone
    "reserve_1": "BNP.PA",  # EU
    "reserve_2": "JPM",  # US
}

OTHER_SQUAD = {
    "champion": "MC.PA",
    "veteran": "KO",
    "marksman": "AIR.PA",
    "saboteur": "TSLA",
    "priority_target": "TTE.PA",
    "reserve_1": "GLE.PA",
    "reserve_2": "PEP",
}


@dataclass
class League:
    db: Db
    id: uuid.UUID
    host: uuid.UUID
    users: dict[str, uuid.UUID]
    members: dict[str, uuid.UUID]
    outsider: uuid.UUID

    def squad_ids(self, squad: dict[str, str]) -> dict[str, int]:
        return {slot: self.db.instrument(ticker) for slot, ticker in squad.items()}

    def save_squad(self, who: str, squad: dict[str, str] | None = None) -> None:
        self.db.set_now(T_BRIEFING)
        self.db.rpc(
            self.users[who],
            "save_squad",
            p_league=self.id,
            p_units=self.squad_ids(squad or VALID_SQUAD),
        )

    def give_ammo(self, who: str, amount: int) -> None:
        self.db.exec_admin(
            "insert into public.ammo_ledger (league_id, member_id, week, delta, reason) "
            "values (%s, %s, %s, %s, 'test')",
            (self.id, self.members[who], WEEK, amount),
        )

    def open_resupply(self) -> None:
        self.db.exec_admin(
            "update public.weeks set resupply_opens_at = %s, debrief_at = %s "
            "where league_id = %s and week = %s",
            (RESUPPLY_OPENS_AT, DEBRIEF_AT, self.id, WEEK),
        )

    def apply_order(self, attacker: str, order_type: str, target: str) -> None:
        """Inserts an already resolved order, as the lock job would."""
        self.db.exec_admin(
            "insert into public.orders (league_id, week, member_id, type, target_member_id, "
            "order_window, cost, status, created_at, resolved_at) "
            "values (%s, %s, %s, %s, %s, 'briefing', 1, 'applied', %s, %s)",
            (
                self.id,
                WEEK,
                self.members[attacker],
                order_type,
                self.members[target],
                T_BRIEFING,
                LOCK_AT,
            ),
        )


def make_league(
    db: Db,
    commanders: dict[str, str] | None = None,
    start: bool = True,
    max_players: int = 5,
) -> League:
    commanders = {"A": "bastion", "B": "hunter", "C": "prophet", **(commanders or {})}
    users = {name: db.create_user() for name in commanders}
    outsider = db.create_user()
    colors = ["#1f3a5f", "#c2410c", "#166534", "#7c3aed", "#b91c1c"]
    db.set_now(T_BEFORE_START)
    names = list(commanders)
    league_id = db.rpc(
        users[names[0]],
        "create_league",
        p_name="Test league",
        p_max_players=max_players,
        p_campaign_weeks=8,
        p_drone_enabled=True,
        p_pseudo=f"P{names[0]}x",
        p_commander=commanders[names[0]],
        p_avatar_color=colors[0],
    )
    code = db.fetch_admin("select invite_code from public.leagues where id = %s", (league_id,))[0][
        "invite_code"
    ]
    for index, name in enumerate(names[1:], start=1):
        db.rpc(
            users[name],
            "join_league",
            p_code=code,
            p_pseudo=f"P{name}x",
            p_commander=commanders[name],
            p_avatar_color=colors[index],
        )
    for name in names:
        db.rpc(users[name], "set_ready", p_league=league_id, p_ready=True)
    if start:
        db.rpc(users[names[0]], "start_campaign", p_league=league_id)
        db.exec_admin(
            "update public.instrument_weeks set in_conflict_zone = false where week = %s", (WEEK,)
        )
        db.exec_admin(
            "insert into public.instrument_weeks (instrument_id, week, in_conflict_zone) "
            "select id, %s, ticker = any(%s) from public.instruments "
            "on conflict (instrument_id, week) "
            "do update set in_conflict_zone = excluded.in_conflict_zone",
            (WEEK, list(CONFLICT_ZONE)),
        )
    rows = db.fetch_admin(
        "select member_id, user_id from public.league_members where league_id = %s", (league_id,)
    )
    by_user = {row["user_id"]: row["member_id"] for row in rows}
    members = {name: by_user[user] for name, user in users.items()}
    drone = [row["member_id"] for row in rows if row["user_id"] is None]
    if drone:
        members["Drone"] = drone[0]
    return League(db, league_id, users[names[0]], users, members, outsider)


@pytest.fixture
def league(db: Db) -> League:
    return make_league(db)
