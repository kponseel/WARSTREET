# CLAUDE.md — WARSTREET

Weekly fantasy stock-market game for a private league of 3 to 5 friends.
Futuristic-army theme, free-for-all: every player fights every other player.
Real EU and US stock prices drive the scores; players draft a 5-unit squad on the weekend,
play orders against each other mid-week, and are ranked every Friday night.

The game is called **WARSTREET** (one word, all caps in logos and titles). The name lives in
ONE place: `web/src/config.ts` (`GAME_NAME`) and `engine/config.py` (`GAME_NAME`).
Never hardcode it elsewhere.

The game is **bilingual: English and French**. English is the reference language.

## Source of truth

Read these before any task. If code and docs disagree, the docs win; if the docs are
ambiguous, stop and ask instead of guessing.

- `docs/GAME_RULES.md` — the full rules as an engine spec (formulas, timings, orders, edge cases)
- `docs/ARCHITECTURE.md` — stack, data model, security model, jobs, lobby flow
- `data/instruments.csv` — the 100-stock catalogue (seed)
- `prompts/` — the build plan, one prompt per milestone, run in order

## Stack (do not change without asking)

- `web/` — Vite + React + TypeScript (strict), mobile-first PWA, deployed to GitHub Pages.
  HashRouter (Pages has no SPA fallback). Light theme only. UI in English and French (i18n).
- `supabase/` — Postgres schema, RLS policies, RPC functions, seed, as SQL migrations.
  Supabase Auth (email magic link), Realtime for live scores and the event feed.
- `engine/` — Python 3.12 package: scoring, commanders, orders, ranking, market calendar.
  Pure functions, no I/O. This is the ONLY place game maths lives.
- `jobs/` — Python scripts run by GitHub Actions: price fetch, phase transitions, scoring,
  Front Dispatch (gazette). They call `engine/` and write to Postgres directly (`SUPABASE_DB_URL`).
- `.github/workflows/` — CI (lint + tests), Pages deploy, `tick` cron, weekly heartbeat.

## Hard rules

1. **Public repository.** Never commit secrets, `.env` files, real emails or league data.
   The Supabase anon key is public by design; the database connection string
   (`SUPABASE_DB_URL`) exists ONLY in GitHub Actions secrets. Add `.env*` to `.gitignore` on day one.
2. **RLS is the security boundary.** Anyone can read the frontend code and the anon key.
   Clients never write game tables directly: every player action goes through a Postgres
   RPC function (`security definer`) that validates deadlines, ownership and game rules.
   Hidden information (squads before lock, the Shadow commander, force fields, jamming)
   must be enforced in RLS, membership-filtered views, or tables the jobs write already
   masked (Realtime only watches tables), never only in the UI.
3. **Time.** Store UTC everywhere. Display Europe/Paris. Never hardcode market hours:
   derive them from `exchange_calendars` (DST mismatches happen ~3 weeks a year).
4. **Jobs are idempotent.** A cron run can be late, skipped or doubled. Every transition is
   keyed in `job_runs` (`league_id, week, transition`) or, for global market work, in
   `market_runs` (`week, transition`), and computed from "what should be true now", so
   re-running a tick never double-scores.
5. **Game maths only in `engine/`**, covered by pytest. The frontend displays numbers it
   reads from the database; it never recomputes scores.
6. **Tunable values live in `engine/config.py`** (multipliers, commander values, bonuses,
   points tables) and are mirrored to a generated `game_config` table (checked by a sync
   test) that RPCs read for validation and the UI reads for display. No magic numbers,
   in Python or in SQL.
7. Brand/IP: original universe. Do not use Warhammer 40,000 names, factions, emblems or
   terms (Games Workshop trademark). Commander emblems are simple original SVG glyphs.

## Conventions

- Code, identifiers, commits and docs: English.
- UI strings: never inline. One key set in `web/src/i18n/en.ts` (reference) and
  `web/src/i18n/fr.ts`; a test fails if a key is missing in either file. Labels for game
  terms come from `docs/GAME_RULES.md` §13. Language = `profiles.locale`, defaulting to the
  browser language (fr* → French, else English), switchable in the header.
- Server messages (RPC errors, Front Dispatch, events) are stored as a message key + variables,
  never as finished text, so each player reads them in their own language.
- Numbers and dates formatted with `Intl` for the active locale; times shown in Europe/Paris
  with the zone label.
- Python: ruff + pytest, type hints. TypeScript: eslint + vitest, no `any`.
- SQL: one migration per change, never edit an applied migration.
- Conventional commits (`feat:`, `fix:`, `chore:`…). One milestone = one branch = one PR.
- Before writing code for a milestone, show a short plan and wait for approval.
- At the end of a milestone: run all tests, list what changed, list what is NOT done.

## Commands (fill in as the repo grows)

```
# web (Node 22, .nvmrc)
cd web && npm install && npm run dev        # local dev
npm run lint && npm run test && npm run build
# engine + jobs (Python 3.12, from the repo root)
python3.12 -m venv .venv && . .venv/bin/activate && pip install -e "engine[dev]" -r jobs/requirements.txt
pip install -r supabase/tests/requirements.txt
ruff check . && ruff format --check . && pytest -q --cov=engine --cov-fail-under=90
# balance check (Monte Carlo win rate per commander)
python -m engine.simulate --players 4 --weeks 8 --runs 2000
python -m jobs.validate_tickers                    # check the 100 tickers (network)
python -m jobs.dry_run --week 2026-10-19 --out /tmp/week.json  # one real week, no DB
# database tests (Supabase CLI): supabase db start, then
WARSTREET_TEST_DB_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres WARSTREET_TEST_DB_PREPARED=1 pytest -q supabase/tests
# web end-to-end against a local Supabase (Docker): supabase start, build web/ with the local
# VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY, then: cd web && npm run e2e && npm run a11y
# regenerate supabase/seed.sql (and web/src/content/gameConfig.generated.ts) after changing
# engine/engine/config.py or data/instruments.csv
python supabase/scripts/generate_seed.py
# regenerate the PWA icons from web/public/icon.svg (needs Playwright + Chromium)
cd web && node scripts/generate-icons.mjs
# one tick, as the cron runs it (fake clock with --now)
python -m jobs.tick --now 2026-11-13T21:45:00Z
# dev mode on the local Supabase (docs/DEV.md): bots + simulated clock, inspect, tick logs
python -m jobs.dev league --me you@example.test --bots 3
python -m jobs.dev advance --league <id> --to lock|monday|resupply|thursday|debrief|next|end
python -m jobs.dev inspect --league <id>; python -m jobs.dev logs --errors
# replay a past week end-to-end against a local or dev database
python -m jobs.replay --league demo --week 2026-W43 --db postgresql://...
# secrets scan of the whole git history (CI runs it); --staged before a commit
python tools/scan_history.py
```
