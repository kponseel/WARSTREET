# 04 — Jobs, tick state machine and GitHub Actions

Read `docs/ARCHITECTURE.md` §2 (platform facts), §6 and `docs/GAME_RULES.md` §2, §4, §10.

## Goal
`jobs/tick.py` moves every active league through its week, idempotently, from a cron that
may be late or doubled. Plus a replay tool to play a past week in minutes.

## Do
1. Plan first: transition list, how "now" maps to expected state, `job_runs` keys,
   failure handling. Wait for my OK.
2. `jobs/db.py` (Supabase with the service role key from env, never logged).
3. `jobs/tick.py`: every transition of ARCHITECTURE §6, each guarded by `job_runs`.
   A `--now` flag to inject a fake clock.
4. `jobs/dispatch.py`: Front Dispatch for the 3 editions (GAME_RULES §10). Store
   `template_key` + `vars` + `variant` in `events`; the English and French template texts
   live in the web i18n files (3+ variants per template, same variant index in both
   languages). Keep a Python renderer for tests and the PR preview.
5. `jobs/replay.py --league <id> --week <YYYY-Www>`: runs every transition of that past
   week in order with historical daily bars and a fake clock.
6. Workflows: `tick.yml` (*/15 weekdays 06–22 UTC, hourly weekends, workflow_dispatch,
   `concurrency: tick`), `heartbeat.yml` (weekly commit of `status/heartbeat.json`).
7. Logs must never print secrets, emails or JWTs.

## Acceptance
- Running the same tick twice changes nothing the second time (test).
- A replay of a real past week on a dev league produces final scores, ranks, campaign
  points, badges and three Front Dispatches. Paste the Friday Dispatch in the PR, in EN and FR.
- List the GitHub secrets I must create.
