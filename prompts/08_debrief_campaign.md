# 08 — Debrief, Front Dispatch, campaign

Read `docs/GAME_RULES.md` §4, §8, §9, §10.

## Goal
Friday night is the social moment: a clear ranking, the story of the week, and badges that
people will tease each other about.

## Do
1. Plan first. Wait for my OK.
2. `#/l/:id/debrief/:week`: weekly ranking with campaign points earned, expandable PF
   breakdown per player (every line of the engine `breakdown`), feats, badges, best and
   worst unit, Drone verdict (each player's `pf_picking` against the Drone, which decides
   `rusty`), the Front Dispatch in the reader's language.
3. `#/l/:id/campaign`: standings, points per week chart, badge collection, Final Assault
   banner, end-of-campaign podium.
4. Badges displayed next to pseudos everywhere during the following week.
5. A share card (image generated client-side) of the weekly podium for the group chat.

## Acceptance
- Golden weeks from milestone 02 render exactly their expected breakdowns.
