# 05 — Web app: auth, home and lobby

Read `docs/ARCHITECTURE.md` §7–8 and `docs/GAME_RULES.md` §1, §5.

## Goal
Friends can log in, create a league, share a join link, pick a pseudo, a commander and an
avatar, get ready, and the host can start the campaign.

## Do
1. Plan first: components, routes, data hooks. Wait for my OK.
2. Design system: light theme only, tokens in one CSS file, mobile-first, readable contrast
   (dark text on light backgrounds; no grey-on-dark). Futuristic-army look with original
   SVG emblems for the 7 commanders (simple geometric glyphs, nothing from Warhammer).
3. Login (ARCHITECTURE §5): magic link with the PKCE flow (exchange `?code=` before the
   HashRouter mounts, then clean the URL) **and** a 6-digit code field for the iOS
   home-screen app. Keep the pending `#/join/:code` across the login round-trip.
   Then `#/`, `#/join/:code`, `#/l/:id/lobby` with a commander picker showing
   each passive and constraint, avatar colour picker, ready toggle, live member list
   (Realtime on the `league_members` table), a copy-invite-link button, a leave button
   (lobby only), and a start-campaign button for the host (≥3 ready). The header language
   switch calls `set_locale`.
4. RPC error codes translated through i18n, in the player's language.
5. `#/rules`: rules summary + glossary from `web/src/content/rules.{en,fr}.ts`, labels
   from GAME_RULES §13.

## Acceptance
- Playwright smoke: two browser contexts, one creates, one joins by code, both ready,
  host starts. Runs in CI against a dev project or mocks (tell me which).
- Lighthouse mobile: accessibility ≥ 95.
