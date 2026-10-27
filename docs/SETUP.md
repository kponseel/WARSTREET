# WARSTREET — Claude Code starter pack

Everything Claude Code needs to build the game in a public GitHub repo, milestone by milestone.

## What's inside

| File | Role |
|---|---|
| `CLAUDE.md` | Project memory: stack, hard rules (public repo, RLS, time, idempotence), conventions |
| `docs/GAME_RULES.md` | Rules v2.1 as an engine spec, adapted to 3–5 players |
| `docs/ARCHITECTURE.md` | Stack, data model, security model, jobs, lobby flow, screens, tests |
| `data/instruments.csv` | The 100 stocks (50 EU / 50 US) with exchange calendars |
| `prompts/00…09` | One prompt per milestone, to run in order |
| `docs/SETUP.md` | This file |

## Before you start (manual, ~30 min)

1. **GitHub**: create a public repo `warstreet`, clone it, copy this pack to the root.
   Settings → Pages → Source: *GitHub Actions*.
2. **Supabase**: create a free project. Note the project URL, the anon key and the
   database connection string: Connect → *Session pooler* (IPv4, port 5432; GitHub
   runners have no IPv6), with the database password filled in. Auth → URL configuration: set the Site URL and add the redirect URL
   `https://<you>.github.io/<repo>/`.
3. **Email (required)**: Supabase's built-in email only reaches members of your Supabase
   organization, about 2 emails per hour, so your friends would never receive a login
   email. In Auth → SMTP settings, plug in a custom SMTP provider with a free tier, e.g.
   Brevo, Resend (needs a domain you own) or Gmail with an app password. Then:
   - Auth → Rate limits: raise the email limit to fit your league (e.g. 30 per hour).
   - Auth → Email templates → Magic link: keep the link **and** add the 6-digit code
     `{{ .Token }}`, so players on an iPhone home-screen app can type the code instead.
   - Send yourself a test login before inviting anyone.
   The SMTP password is entered in the Supabase dashboard only, never in the repo.
4. **GitHub secrets** (Settings → Secrets and variables → Actions):
   secret `SUPABASE_DB_URL` (the session pooler connection string, used by `tick.yml`);
   variables `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.
   The connection string never goes anywhere else (no file, no log, no frontend).
5. **First tick**: Actions → Tick → *Run workflow*. Then the cron takes over
   (`*/15` on weekdays, hourly on weekends). `heartbeat.yml` commits once a week so
   GitHub never disables the schedule.

## How to run the prompts

1. Open Claude Code at the repo root. It reads `CLAUDE.md` automatically.
2. For each milestone: new branch → paste the prompt file content (or
   "Read prompts/0X_….md and execute it") → approve the plan → review the diff → merge.
3. Order: 00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09.
   02 (engine) and 05 (lobby UI) can run in parallel once 01 is merged.
4. Use `python -m jobs.replay --league demo --week 2026-W43 --db <dev or local URL>`
   (milestone 04) to play a past week in minutes before inviting friends.

## Rename the game

Change `GAME_NAME` in `web/src/config.ts` and `engine/config.py`, the repo name, and the
title in `README.md`. Nothing else references it.

## GitHub "About" box

- **Description**: Weekly fantasy stock-market war game for friends. Draft 5 real EU & US stocks, attack your rivals with orders, climb the free-for-all leaderboard. EN/FR.
- **Topics**: `fantasy-game`, `stock-market`, `multiplayer`, `pwa`, `react`, `supabase`, `github-actions`, `python`, `game`
