# 02 — Game engine (Python, pure)

Read `docs/GAME_RULES.md` entirely. It is the spec; do not invent rules.

## Goal
`engine/` computes everything about a week from plain data, with no I/O:
segment returns, unit PF, orders, commanders, feats, badges, ranks, campaign points,
ammo income, Bounty, Drone squad, Conflict Zone selection, coefficients.

## Do
1. Plan first: module list, dataclasses (`Instrument`, `RefPrices`, `Unit`, `Squad`,
   `Order`, `PlayerWeek`, `WeekResult`…) and the public functions. Wait for my OK.
2. `engine/config.py` holds every number (multipliers, REF_VOL, clamps, bonuses, points
   tables, commander values). Nothing hardcoded elsewhere.
3. Implement the scoring order of GAME_RULES §4 exactly, producing a `breakdown` dict that
   explains every PF (the UI will render it line by line).
4. Tests: one per formula, one per commander, one per order, one per feat and badge, every
   edge case of §12, plus 3 golden weeks (fixture prices → expected breakdown JSON) with
   3, 4 and 5 players including swaps, a pact betrayal, a blocked attack and the Drone.
5. A small CLI `python -m engine.simulate --players 4 --weeks 8 --runs 2000` that runs the
   Monte Carlo balance check (random returns, t-distribution, market correlation 0.4) and
   prints campaign win rates per commander. Fair share = 1 / players.

## Acceptance
- `pytest -q` green, coverage of `engine/` ≥ 90 %.
- Simulator output for 3, 4 and 5 players pasted in the PR description, with any commander
  outside ±30 % of the fair share flagged and a proposed value change.
