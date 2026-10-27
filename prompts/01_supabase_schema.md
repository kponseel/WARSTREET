# 01 — Supabase schema, RLS and RPC

Read `docs/ARCHITECTURE.md` §4–5 and `docs/GAME_RULES.md` §1, §3, §6, §7.

## Goal
The full database: tables, enums, RLS policies, read views and the lobby + squad + order RPC
functions, with tests proving the security table of ARCHITECTURE §5.

## Do
1. Plan first: list migrations, policies and RPC signatures. Wait for my OK.
2. Migrations for every table of §4. `game_config` seeded from the values in GAME_RULES.
3. `seed.sql` loading `data/instruments.csv` (generate the SQL from the CSV with a script
   in `supabase/scripts/`, do not hand-type 100 rows).
4. RLS: enable on every table. No client INSERT/UPDATE/DELETE on game tables.
5. RPC (`security definer`, `set search_path = public`): `create_league`, `join_league`,
   `update_member`, `set_ready`, `start_campaign`, `save_squad`, `swap_unit`, `play_order`,
   `propose_pact`, `accept_pact`. Each checks auth, membership, phase, deadline and the rules
   (2 EU / 2 US, veteran region, conflict zone, unique instrument, reserve composition,
   ammo balance and cost incl. Bounty discount, attack cap of 2, once-per-week orders,
   Berserker restrictions, Shadow immune to intel, one pact per week).
   Return errors as stable codes (e.g. `SQUAD_NEEDS_2_EU`) with variables; the UI
   translates them (EN/FR). Add `profiles.locale`.
6. Views: `orders_public`, `scores_live_public`, `squads_visible`, `ammo_balance`.
7. Tests in `supabase/tests/`: for each row of ARCHITECTURE §5, prove what player A,
   player B and an outsider can and cannot read; for each RPC, one success and every
   rejection path.

## Acceptance
- `supabase db reset` (local) or a fresh dev project applies everything without errors.
- All tests pass. Show me the RLS matrix as a table of test names → result.
- List anything in the rules you could not enforce in SQL and how you propose to handle it.
