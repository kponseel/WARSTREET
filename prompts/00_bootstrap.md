# 00 — Bootstrap the repository

Read `CLAUDE.md`, `docs/ARCHITECTURE.md` and `docs/GAME_RULES.md` fully before anything else.

## Goal
Create the monorepo skeleton so every later milestone has a place to land, with CI green and
a "hello" page live on GitHub Pages.

## Do
1. Show me a short plan first (folders, tooling, workflows). Wait for my OK.
2. Create the layout from ARCHITECTURE §3: `web/` (Vite + React + TS strict, HashRouter,
   vite-plugin-pwa, eslint, vitest), `engine/` (pyproject, ruff, pytest, empty modules),
   `jobs/` (requirements.txt), `supabase/` (migrations folder, empty seed), `status/`.
3. `web/src/config.ts` with `GAME_NAME = "WARSTREET"` and the Supabase client reading
   `import.meta.env.VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY`.
4. `.gitignore` covering `.env*`, `.venv`, `node_modules`, `dist`, `supabase/.temp`.
5. Workflows: `ci.yml` (ruff, pytest, eslint, vitest, build) and `deploy-pages.yml`
   (build `web/` with the `base` set to `/<repo-name>/`, deploy to Pages).
6. i18n from day one: `web/src/i18n/{en,fr}.ts` with typed keys, a `t()` helper, locale
   detection (fr* → fr, else en), a header language switch, and a vitest that fails when a
   key exists in one language but not the other. Placeholder home page in both languages,
   light theme.
7. `README.md`: what the game is in 5 lines, how to run locally, how to deploy.

## Acceptance
- `npm run build`, `npm run test`, `pytest -q` all pass locally and in CI.
- No secret, key or email anywhere in the repo (grep for it and show me the result).
- Tell me exactly which GitHub settings I must change by hand (Pages source = Actions,
  repository variables) and which I must not.
