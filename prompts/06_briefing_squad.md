# 06 — Briefing: squad builder, briefing orders, pacts

Read `docs/GAME_RULES.md` §3, §6, §7 and `docs/ARCHITECTURE.md` §5.

## Goal
In under 5 minutes on a phone, a player builds a valid squad, sees why it is invalid if it
is, plays briefing orders and proposes or accepts a pact.

## Do
1. Plan first. Wait for my OK.
2. Catalogue as unit cards: name, flag (EU/US), sector, display class, coefficient, last
   week's return, weather badge (En feu, Surgelée, Résultats cette semaine, Montagnes russes).
   Filters: region, sector, class, Conflict Zone, search.
3. Slot board with the 5 front slots + reserve, live validation messages mirroring the RPC
   rules, a "Drone, propose-moi une escouade" button (random valid squad).
4. Save via `save_squad`; show the lock countdown (Sunday 23:59 Paris).
5. Orders panel: ammo balance, briefing orders with cost (Bounty discount shown), target
   picker, confirmation step. Force field marked as hidden.
6. Pacts: propose, accept, see active pacts.

## Acceptance
- Every RPC rejection path reachable from the UI shows its message.
- Works at 360 px width without horizontal scroll.
