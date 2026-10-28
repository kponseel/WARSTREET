# Dev mode and debugging

How to play whole games locally in minutes, and how to find out what went wrong.

## 1. Local stack

```
supabase start          # Postgres + Auth + REST + Realtime + Mailpit (Docker)
cd web
VITE_SUPABASE_URL=http://127.0.0.1:54321 VITE_SUPABASE_ANON_KEY=<anon key from `supabase status`> npm run dev
```

Login emails land in Mailpit: http://127.0.0.1:54324 (the 6-digit code and the link).
Log in once with any address (e.g. `you@example.test`) so the account exists.

## 2. Simulated games: `python -m jobs.dev`

The dev mode runs the **whole database on a simulated clock**: a row in
`private.dev_clock` (migration 12) makes `private.clock()`, which every deadline check uses,
return the simulated time, for every session, the app's included. Production never has
that row. The tool refuses any database that is not on localhost.

```
# a league of 3 bots + you, week 1 = the last complete market week, briefing open
python -m jobs.dev league --me you@example.test --bots 3

# step the clock; bots play through the real RPCs; the same tick as the cron runs at
# every instant where something happens (captures, phases, dispatches, debrief)
python -m jobs.dev advance --league <id> --to lock        # Sunday 23:59:59 Paris
python -m jobs.dev advance --league <id> --to monday      # EU open + 10 min, Dispatch
python -m jobs.dev advance --league <id> --to resupply    # Wednesday after the US close
python -m jobs.dev advance --league <id> --to thursday    # resupply closed, Dispatch
python -m jobs.dev advance --league <id> --to debrief     # Friday night: scores, badges
python -m jobs.dev advance --league <id> --to next        # next week's briefing
python -m jobs.dev advance --league <id> --to end         # the rest of the campaign
python -m jobs.dev advance --league <id> --to 2026-11-04T18:00Z

python -m jobs.dev inspect --league <id>   # phase, credits, squads, orders, pacts, runs, events
python -m jobs.dev logs --last 5           # the last ticks with their log lines
python -m jobs.dev logs --errors           # failed ticks, warnings and errors only
python -m jobs.dev clock                   # show; --at ISO to set; --clear for real time
```

Options: `--bots N`, `--me EMAIL` (repeat), `--week last|next|2026-W43`, `--weeks 4..10`,
`--lobby` (stay in the lobby to test it), `--prices auto|real|synthetic`, `--no-bots`,
`--json` (scripts and end-to-end tests), `-v` (every transition line).

**Prices.** A campaign that is fully over uses real Yahoo bars (cached in
`.cache/prices/`, so a second run is offline); otherwise synthetic, deterministic random
walks (`jobs/sim.py`), so a campaign never jumps from real to synthetic prices.

**Bots** (`jobs/bots.py`) draft a random valid squad, may play one order per window,
propose and answer pacts and make a swap, all through the player RPCs, seeded by
(league, week, bot): re-running a window repeats the same decisions and never doubles a
move.

A full 4-week campaign with 4 bots takes about two minutes. `jobs.replay` is the
scripted, single-week version used for the milestone 04 demo.

## 3. Logs and the tick journal

- Job logs carry their context: `[league=… week=… transition=…]`. `--log-format json`
  prints one JSON object per line (GitHub Actions, `jq`). Connection strings, passwords,
  emails and tokens are redacted before any line is written (`jobs/logs.py`).
- Every tick is journaled in `private.tick_runs` (game time, transitions done, the log
  lines, the error), kept 30 days, and summarised in `public.system_status` (last tick,
  consecutive failures, price freshness, dev clock), which the app can read.
- A transition that fails is rolled back with its idempotence key and logged with its
  traceback; the other leagues still run; the tick is marked failed. `jobs.tick` exits
  with an error (GitHub's failure email) only from the 2nd failure in a row.
- On a hosted project: `select * from private.tick_runs order by id desc limit 5;` in the
  SQL editor.
- In the app, `#/status` ("Server status" at the bottom of the home page) shows the last
  tick, its result, the failures in a row and the last price capture, for every player.
- A provider down on Friday night: `capture_p_end` retries for 2 hours, then uses the
  last live quote of the week (`source = 'fallback:last_quote'`, a warning in the tick
  log, a notice in the debrief). Rehearse it with `supabase/tests/test_jobs.py -k
  provider_down`.

## 4. In the app: `#/debug`

Open the app with `?debug=1` (e.g. `http://127.0.0.1:5173/?debug=1#/`) to turn the debug
mode on (`?debug=0` turns it off). A "Debug" link appears in the header. The page shows:

- the build (commit), the user id, the server clock offset (and "simulated clock" in dev);
- the last server tick (`system_status`);
- the tab's log: every RPC call (duration, refusal code and variables), Realtime channel
  states, uncaught errors and rejected promises;
- "Copy the report": a JSON bug report without emails, tokens or passwords.

Countdowns use the server clock (`public.server_time()`), so a phone with a wrong clock
still shows the right deadlines, and the dev mode's simulated time shows in a banner.

## 5. End-to-end tests

`web/e2e` runs against the local stack: `lobby.spec.ts` (login, create, join, start),
`briefing.spec.ts` (squad, orders, pacts, then the lock), `front.spec.ts` (live front and
resupply), `debrief.spec.ts` (Friday ranking, breakdown, Drone verdict, share card,
campaign) and `narrow.spec.ts` (every screen of a week at 360 px: no overflow, no clipped
label, no axe violation; in English while French is off, in French once it is back) and
`tutorial.spec.ts` (the first-launch tutorial, its "don't show again" box and the Help
link). The others log in with the tutorial already dismissed (`logIn` in `e2e/session.ts`). The last four create a league of bots with
`jobs.dev` and move the clock.
The dev clock is global, so the tests run one at a time (`workers: 1`). CI runs them in
the `e2e` job.
