# 03 — Market data and calendars

Read `docs/GAME_RULES.md` §2, §3, §11, §12 and `docs/ARCHITECTURE.md` §6.

## Goal
Reliable reference prices and live prices for the 100 instruments, driven by exchange
calendars, never by hardcoded hours.

## Do
1. Plan first. Wait for my OK.
2. `engine/calendar.py`: wrap `exchange_calendars` for XPAR, XETR, XAMS, XMIL, XMAD, XHEL,
   XCSE, XNYS. Functions: sessions of a week, first open of the week, first open on/after
   Thursday, last close of the week, and the phase timestamps of GAME_RULES §2
   (`lock_at`, `resupply_opens_at`, `resupply_closes_at`, `debrief_at`) in UTC.
   Tests for a normal week, a DST-mismatch week (e.g. the week of 2026-10-26), US
   Thanksgiving with its half-day Friday, May 1st in Europe, Easter Monday, Friday
   2026-12-25 (all closed) and Friday 2026-07-03 (US closed).
3. `jobs/prices.py` with a `PriceProvider` protocol, a `YFinanceProvider`
   (`auto_adjust=False`: raw prices) **and a working fallback provider** (Yahoo often
   rate-limits GitHub runners): batch live quotes, daily bars (open/close), dividends with
   ex-dates, splits, market cap, earnings dates, 12-week weekly returns.
   Retries with backoff, then fallback; missing data reported, never invented.
4. A validation script that checks all 100 tickers of `data/instruments.csv` against the
   provider and prints a report (OK / missing / wrong currency). Do not drop tickers silently.
5. `engine/conflict_zone.py`, `engine/weather.py` and coefficient computation (`vol12w`,
   `coef`, display class). Dividend-to-segment assignment per GAME_RULES §2, with tests
   for an ex-date on the first and on the last session of a segment.

## Acceptance
- Ticker validation report pasted in the PR.
- Calendar tests green. A dry run fetching one week of real reference prices into a local
  JSON file (not committed).
