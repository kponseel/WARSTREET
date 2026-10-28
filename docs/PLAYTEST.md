# First playtest

How to run the first real campaign with friends, what to check in week 1, and the known
limits. Setup of the services themselves is in [SETUP.md](SETUP.md); the dev mode used to
rehearse is in [DEV.md](DEV.md).

## 1. Before inviting anyone (about one hour)

1. **Services** (SETUP.md): Supabase project with the migrations and the seed, custom
   SMTP, the login email template (link **and** 6-digit code) in both "Magic link" and
   "Confirm signup", redirect URL = the Pages URL, GitHub secret `SUPABASE_DB_URL`,
   repository variables `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
2. **Rehearse locally** with the dev mode: `supabase start`, then
   `python -m jobs.dev league --me you@example.test --bots 4` and
   `python -m jobs.dev advance --league <id> --to end`. Open the app at each phase.
3. **First tick in production**: Actions → Tick → Run workflow. Then open the app,
   "Server status" at the bottom of the home page (`#/status`): "Everything is running",
   last tick a few minutes old.
4. **Security checklist** (§5 below), once.
5. **Login from a phone that is not yours** (a friend's address): the email arrives
   (check spam), the code works, the link works.
6. Install the app on a phone home screen (Share → Add to Home Screen) and log in with the
   code inside the installed app.

## 2. Inviting friends

- Create the league on a **Wednesday or Thursday**: friends join, pick a pseudo, a
  commander and a colour, and tap "I'm ready". With 3+ ready, start the campaign before
  **Sunday 11:59** (Paris) so week 1 is the coming Monday (12 h minimum before the lock).
- Share the invite link from the lobby ("Copy the invite link") in the group chat. A
  friend who is not logged in yet is brought back to the join page after the login.
- Tell everyone: one squad per week before **Sunday 23:59**, resupply from Wednesday
  night to **Thursday 08:59**, the debrief on Friday night. Without a squad at the lock,
  one is deployed automatically (the previous week's, or a random valid one).
- Rules: the "Rules" page in the app (English and French).

## 3. First-week checklist

| When (Paris) | Check |
|---|---|
| Saturday | Ammo arrived (+3 each). The Conflict Zone shows in the briefing (Priority Target filter). |
| Sunday evening | Everyone saved a squad (or knows the auto squad). Briefing orders paid. |
| Monday after 09:10 | Squads locked; live leaderboard moving; the Monday Front Dispatch is in the feed; the Shadow is not on the board; a jammed player shows `???`. |
| Wednesday night | Resupply open after the US close; swaps and resupply orders work; a Blockaded player sees why not. |
| Thursday 09:10 | Swaps applied (Segment 2 only tags); Thursday Dispatch. |
| Friday ~22:30 | Debrief: ranking, breakdowns, badges, Drone verdict, Friday Dispatch; the share card; the next week's briefing is open. |
| Any time | `#/status` says "Everything is running" (last tick < 20 min old on weekdays); GitHub Actions "Tick" runs are green. Two failed ticks in a row email the repository owner (GitHub's failed-workflow email). |

If something looks wrong: ask the player to open the app with `?debug=1`, reproduce,
then "Copy the report" from the Debug page and paste it to you. On the server side:
`select * from private.tick_runs where not ok order by id desc limit 5;` in the SQL
editor, and the Actions logs (one JSON line per log with `--log-format json`).

## 4. Known limits (v1)

- Prices are daily bars plus live quotes from Yahoo (no official feed). A missing price
  is retried for 2 hours. If Yahoo is down on Friday night, the debrief waits, then scores
  on each stock's last live quote of the week and says so in the debrief; a stock with no
  quote at all scores nothing for that segment.
- Player actions are limited to 30 per minute per player (`RPC_RATE_LIMIT_PER_MINUTE`);
  a person never gets there, a script does.
- Live quotes are refreshed every 15 minutes (GitHub Actions cron); GitHub can delay a
  scheduled run by several minutes under load.
- The app is a PWA: notifications are not implemented; open it to see what happened.
- One league can have 3 to 5 humans plus the Drone. Commanders cannot be changed after the
  start. A campaign cannot be paused.
- The Supabase free tier pauses a project after a week without activity: the weekly
  heartbeat commit and the tick keep it awake during a campaign.

## 5. Security checklist (once, before the first invite)

The repository is public: anyone can read the app and the anon key. The database is the
boundary (RLS, `security definer` RPCs, masked tables); these settings complete it.

- [ ] **Auth → URL configuration**: Site URL = the Pages URL; redirect URLs = the Pages
  URL only (plus `http://127.0.0.1:5173/**` if you test against production from a laptop).
- [ ] **Auth → SMTP**: custom SMTP configured; a login email reaches an address that is
  **not** a member of the Supabase team (the built-in sender only mails the team).
- [ ] **Auth → Email templates**: "Magic link" and "Confirm signup" both hold the link and
  `{{ .Token }}` (`supabase/templates/magic_link.html`); email OTP length = 6.
- [ ] **Auth → Rate limits**: emails per hour fit the league (30 is plenty); keep the
  default limits on verification and token refresh.
- [ ] **Auth → Providers**: Email on; anonymous sign-ins off; no other provider.
- [ ] **Rate limit hook**: in the SQL editor,
  `select rolconfig from pg_roles where rolname = 'authenticator';` lists
  `pgrst.db_pre_request=private.check_request` (migration 16). If the migration could not
  set it, run its last two statements in the SQL editor.
- [ ] **Secrets**: `SUPABASE_DB_URL` only in GitHub Actions secrets; `python
  tools/scan_history.py` prints `0 finding(s)` (CI runs it on every pull request).

Covered by the tests on every pull request (no action):

- every table has RLS and no client can write one (`supabase/tests/test_rls.py`);
- functions executable by `anon`: only `private.check_request` (the hook, which returns
  at once without a user); by `authenticated`: the player RPCs and the policy helpers;
- every view runs `security_invoker`, except `orders_public`, which masks the Shadow and
  unrevealed force fields itself;
- RPC fuzzing: no identity, an outsider, targets from another league, garbage
  parameters, every action outside its window (`supabase/tests/test_rpc_fuzz.py`);
- the rate limit (`supabase/tests/test_rate_limit.py`).

## 6. Balance (milestone 09 simulation)

`python -m engine.simulate --players N --weeks 8 --runs 8000 --seed 21`, campaign win rate
per commander against the fair share (`1/N`). The simulator drafts with a popularity
bias and plays a random order policy (no pacts, no bluff), so it measures the raw value
of each commander's rule, not how well people use it. One run's noise is about ±3 points
(relative); figures below were checked on three seeds (1, 11, 21).

| Commander | 3 players | 4 players | 5 players | Across seeds |
|---|---|---|---|---|
| Bastion | +7 % | +1 % | +10 % | above fair in all 9 runs (+1 to +20 %) |
| Berserker | −3 % | +0 % | +1 % | fair; slightly low at 3 players (−3 to −5 %) |
| Prophet | −2 % | −1 % | −1 % | fair |
| Hunter | +3 % | +5 % | +5 % | fair to slightly above (−2 to +5 %) |
| Shadow | −0 % | +1 % | −8 % | low at 5 players (−6 to −10 %) |
| Technomancer | −2 % | −3 % | −1 % | slightly low; extra ammo changes nothing here |
| Quartermaster | −3 % | −3 % | −6 % | slightly low at 5 |

Elite unit bonus: 30–37 FP per player and week on average; `rusty` (beaten by the Drone)
about half the player-weeks, as expected from random drafts.

**Proposal** (not applied: it changes the golden weeks and is a game-design call):

1. `BASTION_LOSS_REDUCTION` 5 → **4**. The one consistent outlier; at 4 the Bastion lands
   at +5 / −1 / +7 % (3 / 4 / 5 players), at 3 at +3 / −3 / +5 %.
2. Keep the others for the first campaign. Shadow's hidden score and Technomancer's
   extra ammo are worth more with people than with a random policy (the simulator cannot
   see bluff or well-timed orders); re-check after the playtest with the real orders
   (`private.tick_runs` and `public.orders`).
