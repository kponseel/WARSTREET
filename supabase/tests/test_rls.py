"""RLS matrix of docs/ARCHITECTURE.md §5: for each row, what player A, player B and an
outsider can and cannot read. Plus global guarantees (no client writes, anon, Realtime)."""

import psycopg
import pytest
from conftest import (
    LOCK_AT,
    OTHER_SQUAD,
    T_AFTER_LOCK,
    T_BRIEFING,
    T_DEBRIEF,
    T_RESUPPLY,
    T_S2,
    WEEK,
    Db,
    League,
    make_league,
)

RPCS = {
    "accept_pact",
    "cancel_swap",
    "create_league",
    "decline_pact",
    "join_league",
    "leave_league",
    "league_preview",
    "order_costs",
    "play_order",
    "propose_pact",
    "save_squad",
    "server_time",
    "set_locale",
    "set_ready",
    "start_campaign",
    "swap_unit",
    "update_member",
}
POLICY_HELPERS = {
    "can_see_squad",
    "can_see_swaps",
    "clock",
    "is_jammed",
    "is_league_member",
    "is_shadow",
    "my_member_id",
}


@pytest.fixture
def game(db: Db) -> League:
    league = make_league(db, {"A": "bastion", "B": "hunter", "C": "shadow"})
    league.save_squad("A")
    league.save_squad("B", OTHER_SQUAD)
    league.save_squad("C", {**OTHER_SQUAD, "champion": "SAP.DE"})
    return league


def _count(db: Db, user: object, query: str, params: object = None) -> int:
    return len(db.select(user, query, params))


# Row 1: league, members, weeks, final scores, badges — members of that league.
def test_league_data_is_for_members_only(db: Db, game: League) -> None:
    db.exec_admin(
        "insert into public.scores_final (league_id, week, member_id, pf_total, pf_picking, rank) "
        "values (%s, %s, %s, 10, 10, 1)",
        (game.id, WEEK, game.members["A"]),
    )
    db.exec_admin(
        "insert into public.badges (league_id, week, member_id, code) "
        "values (%s, %s, %s, 'warlord')",
        (game.id, WEEK, game.members["A"]),
    )
    for table, expected in (
        ("leagues", 1),
        ("league_members", 4),
        ("weeks", 1),
        ("scores_final", 1),
        ("badges", 1),
    ):
        query = (
            f"select 1 from public.{table} where "
            + ("id" if table == "leagues" else "league_id")
            + " = %s"
        )
        assert _count(db, game.users["A"], query, (game.id,)) == expected, table
        assert _count(db, game.users["B"], query, (game.id,)) == expected, table
        assert _count(db, game.outsider, query, (game.id,)) == 0, table


# Row 2: own squad, orders, swaps, ammo — owner always.
def test_own_data_is_always_visible_to_its_owner(db: Db, game: League) -> None:
    game.give_ammo("A", 5)
    db.set_now(T_BRIEFING)
    db.rpc(game.users["A"], "play_order", p_league=game.id, p_type="force_field")
    a = game.users["A"]
    assert (
        _count(db, a, "select 1 from public.squad_units where member_id = %s", (game.members["A"],))
        == 7
    )
    assert _count(db, a, "select 1 from public.orders") == 1
    assert db.select(a, "select balance from public.ammo_balance") == [{"balance": 4}]
    for other in (game.users["B"], game.outsider):
        assert _count(db, other, "select 1 from public.orders") == 0
        assert (
            _count(
                db,
                other,
                "select 1 from public.ammo_ledger where member_id = %s",
                (game.members["A"],),
            )
            == 0
        )


# Row 3: other players' squads from lock_at; a Shadow's only from debrief_at.
def test_squads_from_lock_and_shadow_from_debrief(db: Db, game: League) -> None:
    db.exec_admin(
        "update public.weeks set debrief_at = %s where league_id = %s",
        (T_DEBRIEF.replace(minute=30, hour=21), game.id),
    )
    query = "select distinct member_id from public.squads_visible where league_id = %s"
    b = game.users["B"]
    db.set_now(T_BRIEFING)
    assert {r["member_id"] for r in db.select(b, query, (game.id,))} == {game.members["B"]}
    db.set_now(LOCK_AT)
    assert {r["member_id"] for r in db.select(b, query, (game.id,))} == {
        game.members["A"],
        game.members["B"],
    }
    db.set_now(T_DEBRIEF)
    assert {r["member_id"] for r in db.select(b, query, (game.id,))} == {
        game.members["A"],
        game.members["B"],
        game.members["C"],
    }
    assert db.select(game.outsider, query, (game.id,)) == []


# Row 4: a target's draft before lock — only through an intel snapshot for the attacker.
def test_draft_before_lock_only_via_intel(db: Db, game: League) -> None:
    game.give_ammo("A", 5)
    db.set_now(T_BRIEFING)
    a = game.users["A"]
    assert (
        _count(db, a, "select 1 from public.squad_units where member_id = %s", (game.members["B"],))
        == 0
    )
    db.rpc(a, "play_order", p_league=game.id, p_type="intel", p_target_member=game.members["B"])
    assert db.select(a, "select vars->'units' as u from public.events where kind = 'intel'") == [
        {"u": OTHER_SQUAD}
    ]
    assert (
        _count(db, a, "select 1 from public.squad_units where member_id = %s", (game.members["B"],))
        == 0
    )


# Row 5: other players' swaps from resupply_closes_at; a Shadow's from debrief_at.
def test_swaps_visibility(db: Db, game: League) -> None:
    game.open_resupply()
    db.set_now(T_RESUPPLY)
    for who in ("A", "C"):
        db.rpc(
            game.users[who],
            "swap_unit",
            p_league=game.id,
            p_slot="marksman",
            p_reserve_slot="reserve_1",
        )
    query = "select member_id from public.swaps where league_id = %s"
    b = game.users["B"]
    assert db.select(b, query, (game.id,)) == []
    db.set_now(T_S2)
    assert {r["member_id"] for r in db.select(b, query, (game.id,))} == {game.members["A"]}
    db.set_now(T_DEBRIEF)
    assert {r["member_id"] for r in db.select(b, query, (game.id,))} == {
        game.members["A"],
        game.members["C"],
    }
    assert db.select(game.outsider, query, (game.id,)) == []


# Row 6: other players' orders after resolution, via orders_public.
def test_orders_public(db: Db, game: League) -> None:
    db.exec_admin(
        "insert into public.orders (league_id, week, member_id, type, target_member_id, "
        "order_window, cost, status, created_at, resolved_at) values "
        "(%(l)s, %(w)s, %(a)s, 'jamming', %(b)s, 'briefing', 1, 'applied', %(t)s, %(r)s), "
        "(%(l)s, %(w)s, %(c)s, 'blockade', %(a)s, 'briefing', 2, 'applied', %(t)s, %(r)s), "
        "(%(l)s, %(w)s, %(b)s, 'force_field', null, 'briefing', 1, 'pending', %(t)s, null), "
        "(%(l)s, %(w)s, %(a)s, 'pillage', %(b)s, 'resupply', 3, 'pending', %(t)s, null)",
        {
            "l": game.id,
            "w": WEEK,
            "a": game.members["A"],
            "b": game.members["B"],
            "c": game.members["C"],
            "t": T_BRIEFING,
            "r": LOCK_AT,
        },
    )
    rows = db.select(
        game.users["B"], "select type, member_id from public.orders_public order by type"
    )
    # pending pillage and untriggered force field are hidden; the Shadow attacker is masked
    assert rows == [
        {"type": "blockade", "member_id": None},
        {"type": "jamming", "member_id": game.members["A"]},
    ]
    db.exec_admin(
        "update public.orders set status = 'applied', resolved_at = %s where type = 'force_field'",
        (LOCK_AT,),
    )
    assert (
        _count(db, game.users["A"], "select 1 from public.orders_public where type = 'force_field'")
        == 1
    )
    assert db.select(game.outsider, "select 1 from public.orders_public") == []


# Rows 7-8: private live score (owner, not while jammed) and the masked public table.
def test_live_scores(db: Db, game: League) -> None:
    for who in ("A", "B"):
        db.exec_admin(
            "insert into public.scores_live (league_id, week, member_id, pf_live) "
            "values (%s, %s, %s, 12)",
            (game.id, WEEK, game.members[who]),
        )
        db.exec_admin(
            "insert into public.scores_live_public "
            "(league_id, week, member_id, pf_live, rank_live) "
            "values (%s, %s, %s, 12, 1)",
            (game.id, WEEK, game.members[who]),
        )
    assert db.select(game.users["A"], "select member_id from public.scores_live") == [
        {"member_id": game.members["A"]}
    ]
    game.apply_order("B", "jamming", "A")
    assert db.select(game.users["A"], "select 1 from public.scores_live") == []
    assert _count(db, game.users["A"], "select 1 from public.scores_live_public") == 2
    assert _count(db, game.users["B"], "select 1 from public.scores_live_public") == 2
    assert db.select(game.outsider, "select 1 from public.scores_live_public") == []


# Row 9: events filtered by audience.
def test_events_audience(db: Db, game: League) -> None:
    db.exec_admin(
        "insert into public.events (league_id, kind, template_key, audience_member_id) values "
        "(%s, 'dispatch', 'all', null), (%s, 'note', 'for_b', %s)",
        (game.id, game.id, game.members["B"]),
    )
    assert [
        r["template_key"]
        for r in db.select(game.users["A"], "select template_key from public.events")
    ] == ["all"]
    assert sorted(
        r["template_key"]
        for r in db.select(game.users["B"], "select template_key from public.events")
    ) == ["all", "for_b"]
    assert db.select(game.outsider, "select 1 from public.events") == []


# Row 10: profiles — own row only.
def test_profiles_own_row_only(db: Db, game: League) -> None:
    assert db.select(game.users["A"], "select id from public.profiles") == [{"id": game.users["A"]}]


# Row 11: reference data for any authenticated user, nothing for anon.
def test_reference_data(db: Db, game: League) -> None:
    assert _count(db, game.outsider, "select 1 from public.instruments") == 100
    assert _count(db, game.outsider, "select 1 from public.game_config") > 50
    assert (
        _count(db, game.outsider, "select 1 from public.instrument_weeks where week = %s", (WEEK,))
        == 100
    )
    db.as_anon()
    with pytest.raises(psycopg.errors.InsufficientPrivilege), db.conn.transaction():
        db.conn.execute("select 1 from public.instruments")
    db.admin()


# Pacts: active ones are public to the league, proposals only to the two players.
def test_pacts_visibility(db: Db, game: League) -> None:
    db.set_now(T_BRIEFING)
    pact = db.rpc(game.users["A"], "propose_pact", p_league=game.id, p_partner=game.members["B"])
    assert _count(db, game.users["C"], "select 1 from public.pacts") == 0
    assert _count(db, game.users["B"], "select 1 from public.pacts") == 1
    db.rpc(game.users["B"], "accept_pact", p_pact=pact)
    assert _count(db, game.users["C"], "select 1 from public.pacts") == 1
    assert db.select(game.outsider, "select 1 from public.pacts") == []


# --- global guarantees -----------------------------------------------------------------------
def test_clients_cannot_write_any_table(db: Db) -> None:
    rows = db.fetch_admin(
        "select c.relname, r.rolname from pg_class c join pg_namespace n on n.oid = c.relnamespace "
        "cross join (values ('anon'), ('authenticated')) r(rolname) "
        "where n.nspname = 'public' and c.relkind in ('r', 'v') "
        "and has_table_privilege(r.rolname, c.oid, 'insert, update, delete, truncate')"
    )
    assert rows == []
    user = db.create_user()
    db.as_user(user)
    with pytest.raises(psycopg.errors.InsufficientPrivilege), db.conn.transaction():
        db.conn.execute("update public.leagues set status = 'finished'")
    db.admin()


def test_function_exposure(db: Db) -> None:
    def executable(role: str) -> set[str]:
        rows = db.fetch_admin(
            "select n.nspname || '.' || p.proname as f from pg_proc p "
            "join pg_namespace n on n.oid = p.pronamespace "
            "where n.nspname in ('public', 'private') "
            "and has_function_privilege(%s, p.oid, 'execute')",
            (role,),
        )
        return {row["f"] for row in rows}

    # The PostgREST pre-request hook (rate limit) runs as the request's role, anon included.
    assert executable("anon") == {"private.check_request"}
    assert executable("authenticated") == {f"public.{f}" for f in RPCS} | {
        f"private.{f}" for f in POLICY_HELPERS | {"check_request"}
    }


def test_every_table_has_rls(db: Db) -> None:
    rows = db.fetch_admin(
        "select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace "
        "where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity"
    )
    assert rows == []


def test_views_run_as_invoker_except_orders_public(db: Db) -> None:
    rows = db.fetch_admin(
        "select c.relname, coalesce('security_invoker=true' = any(c.reloptions), false) as invoker "
        "from pg_class c join pg_namespace n on n.oid = c.relnamespace "
        "where n.nspname = 'public' and c.relkind = 'v' order by 1"
    )
    assert {r["relname"]: r["invoker"] for r in rows} == {
        "ammo_balance": True,
        "campaign_standings": True,
        "live_returns": True,
        "orders_public": False,
        "squads_visible": True,
    }


def test_realtime_publication(db: Db) -> None:
    rows = db.fetch_admin(
        "select tablename from pg_publication_tables where pubname = 'supabase_realtime' "
        "and schemaname = 'public'"
    )
    assert {r["tablename"] for r in rows} == {
        "scores_live_public",
        "events",
        "league_members",
        "weeks",
        "pacts",
    }


def test_fake_clock_is_ignored_for_api_sessions(db: Db) -> None:
    db.set_now(T_AFTER_LOCK)
    assert db.fetch_admin("select private.clock() as c") == [{"c": T_AFTER_LOCK}]
    try:
        db.conn.execute("set local session authorization authenticator")
    except psycopg.errors.InsufficientPrivilege:
        pytest.skip("needs a superuser connection to impersonate the API session user")
    db.conn.execute("set local role authenticated")  # what PostgREST does for a player
    clock = db.conn.execute("select private.clock() as c, now() as n").fetchone()
    assert clock is not None and clock["c"] == clock["n"]
