# 04 — Jobs, tick state machine and GitHub Actions

Read `docs/ARCHITECTURE.md` §2 (platform facts), §6 and `docs/GAME_RULES.md` §2, §4, §10.

## Goal
`jobs/tick.py` moves every active league through its week, idempotently, from a cron that
may be late or doubled. Plus a replay tool to play a past week in minutes.

## Do
1. Plan first: transition list, how "now" maps to expected state, `job_runs` keys,
   failure handling. Wait for my OK.
2. `jobs/db.py` (Supabase with the service role key from env, never logged).
3. `jobs/tick.py`: every transition of ARCHITECTURE §6 — market transitions guarded by
   `market_runs`, league transitions by `job_runs`. A `--now` flag to inject a fake clock.
   `live_scores` writes both `scores_live` and the masked `scores_live_public` (no Shadow
   row; jammed rows without PF, rank or per-unit PF; ranks computed without them).
4. `jobs/dispatch.py`: Front Dispatch for the 3 editions (GAME_RULES §10). Store
   `template_key` + `vars` + `variant` in `events`; the English and French template texts
   live in the web i18n files (3+ variants per template, same variant index in both
   languages). Keep a Python renderer for tests and the PR preview. Before debrief, never
   name a Shadow or a jammed player as leader (GAME_RULES §10), with a test.
5. `jobs/replay.py --league <id> --week <YYYY-Www>`: runs every transition of that past
   week in order with historical daily bars and a fake clock.
6. Workflows: `tick.yml` (*/15 weekdays 06–22 UTC, hourly weekends, workflow_dispatch,
   `concurrency: tick`), `heartbeat.yml` (weekly commit of `status/heartbeat.json`).
7. Logs must never print secrets, emails or JWTs.

## Acceptance
- Running the same tick twice changes nothing the second time (test), for market and
  league transitions alike.
- A replay of a real past week on a dev league produces final scores, ranks, campaign
  points, badges and three Front Dispatches. Paste the Friday Dispatch in the PR, in EN and FR.
- List the GitHub secrets I must create.
