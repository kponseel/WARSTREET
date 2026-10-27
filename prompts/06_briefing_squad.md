# 06 — Briefing: squad builder, briefing orders, pacts

Read `docs/GAME_RULES.md` §3, §6, §7 and `docs/ARCHITECTURE.md` §5.

## Goal
In under 5 minutes on a phone, a player builds a valid squad, sees why it is invalid if it
is, plays briefing orders and proposes or accepts a pact.

## Do
1. Plan first. Wait for my OK.
2. Catalogue as unit cards: name, flag (EU/US), sector (label from the sector code,
   GAME_RULES §11), display class, coefficient, last week's return, weather badges read
   from `instrument_weeks.weather` (GAME_RULES §3: On Fire / En feu, Frozen / Surgelée,
   Earnings this week / Résultats cette semaine, Roller Coaster / Montagnes russes).
   Filters: region, sector, class, Conflict Zone, search.
3. Slot board with the 5 front slots + reserve, live validation messages mirroring the RPC
   rules, a "suggest a squad" button (EN "Drone, suggest a squad" / FR "Drone,
   propose-moi une escouade", i18n keys) that fills a random valid squad.
4. Save via `save_squad`; show the lock countdown (Sunday 23:59 Paris).
5. Orders panel: ammo balance, briefing orders with cost (Bounty discount shown), target
   picker, confirmation step. Force field marked as hidden. `intel` shows its snapshot
   right away (with its timestamp: "they may have changed it since").
6. Pacts: propose, accept, decline, see pending and active pacts.

## Acceptance
- Every RPC rejection path reachable from the UI shows its message.
- Works at 360 px width without horizontal scroll.
