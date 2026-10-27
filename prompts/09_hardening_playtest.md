# 09 — Hardening and first playtest

## Goal
Safe to run publicly with real friends for a full campaign.

## Do
1. Security review of the public repo: secrets scan of the full git history, RLS matrix
   re-run, RPC fuzzing for out-of-phase and cross-league calls, rate limits on RPC
   (e.g. max N calls per minute per user), Supabase Auth settings (redirect URLs, email
   rate limits).
2. Ops: alert (GitHub Actions failure email is enough) when a tick fails twice in a row;
   a `status` page in the app showing last tick time and price freshness.
3. Data: what happens if the price provider is down on Friday night (debrief waits, retries,
   then uses last close and flags it). Test it.
4. i18n audit: no hardcoded string in components, every key in EN and FR, French text
   fits the layouts (it is ~20 % longer).
5. Write `docs/PLAYTEST.md`: how to invite friends, the first-week checklist, known limits.
6. Run `engine.simulate` for the real league size and propose final values.

## Acceptance
- Checklist in the PR with every item ticked or explicitly deferred.
