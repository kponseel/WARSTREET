# 07 — The front: live leaderboard and resupply

Read `docs/GAME_RULES.md` §2, §4, §6 and `docs/ARCHITECTURE.md` §5–6.

## Goal
During the week, the app is fun to open: who leads right now, how my units are doing, what
phase of the day it is, and what just happened.

## Do
1. Plan first. Wait for my OK.
2. `#/l/:id/front`: live leaderboard from `scores_live_public` via Realtime (Shadow hidden,
   jammed shown as `???`, Drone tagged), my squad with live PF per unit, current daily phase
   banner (Assaut européen / Feu croisé / Contre-offensive US / marchés fermés) with next
   change time, last update time, event feed.
3. `#/l/:id/resupply` (Wednesday night only): swap from reserve, resupply orders,
   ammo, countdown to Thursday 08:59. Blockaded players see why they cannot act.
4. Empty and closed-market states designed, not blank.

## Acceptance
- Using `jobs/replay.py` with the fake clock, I can watch a whole week unfold in the UI.
- No score computed in the browser: everything displayed comes from the database.
