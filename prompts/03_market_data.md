# 03 — Market data and calendars

Read `docs/GAME_RULES.md` §2, §3, §11, §12 and `docs/ARCHITECTURE.md` §6.

## Goal
Reliable reference prices and live prices for the 100 instruments, driven by exchange
calendars, never by hardcoded hours.

## Do
1. Plan first. Wait for my OK.
2. `engine/calendar.py`: wrap `exchange_calendars` for XPAR, XETR, XAMS, XMIL, XMAD, XHEL,
   XCSE, XNYS. Functions: sessions of a week, first open of the week, first open on/after
   Thursday, last close of the week, phase boundaries in UTC for a league week.
   Tests for a normal week, a DST-mismatch week (e.g. the week of 2026-10-26), US
   Thanksgiving, May 1st in Europe, Easter Monday.
3. `jobs/prices.py` with a `PriceProvider` protocol and a `YFinanceProvider`:
   batch live quotes, daily bars (open/close), dividends, splits, 12-week weekly returns.
   Retries with backoff; missing data reported, never invented.
4. A validation script that checks all 100 tickers of `data/instruments.csv` against the
   provider and prints a report (OK / missing / wrong currency). Do not drop tickers silently.
5. `engine/conflict_zone.py` and coefficient computation (`vol12w`, `coef`, display class).

## Acceptance
- Ticker validation report pasted in the PR.
- Calendar tests green. A dry run fetching one week of real reference prices into a local
  JSON file (not committed).
