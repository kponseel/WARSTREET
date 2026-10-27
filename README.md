# WARSTREET

Weekly fantasy stock-market war game for a private league of 3 to 5 friends. EN/FR.

- Every weekend, draft a squad of 5 real EU and US stocks into slots with multipliers.
- Mid-week, spend ammo on orders: strike a rival's unit, plunder their gains, jam their score.
- Real market prices score every unit; a futuristic-army theme, free-for-all.
- Every Friday night, the week is ranked and campaign points decide the season winner.
- Mobile-first web app (PWA), zero running cost: GitHub Pages + Supabase + GitHub Actions.

Rules: [`docs/GAME_RULES.md`](docs/GAME_RULES.md) · Architecture:
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · First-time setup: [`docs/SETUP.md`](docs/SETUP.md).

## Run locally

Requirements: Node 22 (`.nvmrc`) and Python 3.12 (`.python-version`).

```sh
# web app
cd web
npm install
npm run dev            # http://localhost:5173
npm run lint && npm run test && npm run build

# engine + jobs (from the repository root)
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e "engine[dev]" -r jobs/requirements.txt -r supabase/tests/requirements.txt
ruff check . && ruff format --check . && pytest -q --cov=engine --cov-fail-under=90
python -m engine.simulate --players 4 --weeks 8 --runs 2000   # balance check
python -m jobs.validate_tickers                    # check the 100 tickers (network)
python -m jobs.dry_run --week 2026-10-19 --out /tmp/week.json  # one real week, no DB
```

Database tests (`supabase/tests`, RLS matrix and every RPC path) need a Postgres. With the
Supabase CLI: `supabase db start`, then
`WARSTREET_TEST_DB_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres WARSTREET_TEST_DB_PREPARED=1 pytest -q supabase/tests`.
With any plain Postgres 15+ superuser URL, omit `WARSTREET_TEST_DB_PREPARED`: the tests create
a throwaway database with a small stand-in for Supabase's `auth` schema. Without a URL they
are skipped. After changing `engine/engine/config.py` or `data/instruments.csv`, regenerate
the seed with `python supabase/scripts/generate_seed.py`.

Without Supabase variables the app runs and shows "server connection not configured".
To connect a dev project, create `web/.env.local` (git-ignored) with `VITE_SUPABASE_URL`
and `VITE_SUPABASE_ANON_KEY`. Never put the service role key in a file.

## Deploy

Every push to `main` runs `.github/workflows/deploy-pages.yml`, which builds `web/` with
the base path `/<repo-name>/` and publishes it to GitHub Pages. One-time settings are in
[`docs/SETUP.md`](docs/SETUP.md) (Pages source = GitHub Actions, repository variables
`VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`).
