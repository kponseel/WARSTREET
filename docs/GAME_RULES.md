# GAME_RULES.md — engine specification (rules v2.1, 3 to 5 players)

This document is the contract for `engine/`. Every rule has a code name (used in code and
the database). UI labels in English and French are listed in §13; the French labels shown
in tables below are for reference. All numeric values are defaults from
`engine/config.py` and must stay tunable. Changes since v2 are listed in §14.

**Rounding**: every `round()` in this document means *round half away from zero*
(Python's built-in `round` is banker's rounding: do not use it for game maths).

Values marked **[calibrate]** were balanced by simulation for 8 players and must be
re-checked for 3–5 players before the first real campaign.

---

## 0. Glossary

| Code | UI (FR) | Meaning |
|---|---|---|
| `league` | Ligue | A private game of 3–5 human players (+ optional Drone) |
| `campaign` | Campagne | The season: `campaign_weeks` weeks (default 8) |
| `week` | Semaine | One market week, identified by its Monday date (ISO week) |
| `S1`, `S2` | Segment 1, Segment 2 | The two scoring halves of a week (see §2) |
| `squad` | Escouade | A player's 5 front units + reserve for one week |
| `unit` | Unité | One stock placed in a slot |
| `slot` | Poste | champion, veteran, marksman, saboteur, priority_target, reserve_1..3 |
| `pf` | PF (Points Fantasy) | Weekly score points |
| `campaign_points` | Points de campagne | Points from the weekly rank; decide the winner |
| `ammo` | Munitions | Currency for orders |
| `order` | Ordre | An action card: attack, defense or maneuver |
| `commander` | Commandant | A player's class for the whole campaign (passive ability) |
| `bounty` | La Prime | Marks the campaign leader: cheaper to attack |
| `pact` | Pacte | One-week non-aggression pact between two players |
| `drone` | Drone aléatoire | Ghost player with a random squad, scored but not ranked |
| `conflict_zone` | Zone de conflit | The 8 stocks allowed in the priority_target slot this week |

---

## 1. League lifecycle

- `max_players` 3–5 humans. The host sets it at creation. Drone on by default.
- `campaign_weeks` default 8, allowed 4–10. The last week is the **Final Assault**
  (`is_final`): campaign points ×2.
- States: `lobby` → `active` → `finished`.
- **Lobby**: host creates the league and gets a 6-char invite code (alphabet
  `ABCDEFGHJKMNPQRSTUVWXYZ23456789`). Players join with the code, pick a pseudo (3–16 chars,
  unique in the league), a commander (duplicates allowed), an avatar colour, then mark
  themselves ready. Joining closes at start.
- **Start**: host only, when ≥3 humans are ready. Week 1 is the first market week whose
  lock is at least `min_first_briefing_hours` (default **12 h**) after the start time
  (start before Sunday 11:59:59 Paris → the coming Monday; otherwise the Monday after).
  Commanders are locked at start. Every member plays, ready or not: "ready" only lets the
  host know when to start (a member who never drafts gets an auto squad).
- **Leaving**: a player can leave a league only while it is in `lobby`.
- **End**: after the debrief of the last week → `finished`, final standings frozen.

---

## 2. The week (all times Europe/Paris for display; stored in UTC)

Phases (`week.phase`): `briefing` → `s1_live` → `resupply` → `s2_live` → `debrief`.

| Phase | Window | What players can do |
|---|---|---|
| `briefing` | Previous debrief (Fri ~22:30) → **Sunday 23:59:59** (`lock_at`) | Build squad, briefing orders, pacts |
| `s1_live` | Lock → `resupply_opens_at` | Watch |
| `resupply` | `resupply_opens_at` → **Thursday 08:59:59** (`resupply_closes_at`) | Swap from reserve, resupply orders |
| `s2_live` | Thursday 09:00 → `debrief_at` | Watch |
| `debrief` | `debrief_at` → next briefing | Scoring, ranks, feats, badges, Front Dispatch |

Week 1's briefing opens at league start.

**Phase boundaries** are computed by `engine/calendar.py` when the week is created and
stored on the week (UTC). They are never hardcoded weekdays or hours:

- `lock_at` = Sunday 23:59:59 Europe/Paris before the week's Monday.
- `resupply_opens_at` = close of the last `XNYS` session **on or before Wednesday**
  + 5 min. If `XNYS` has no session Monday–Wednesday, use Wednesday 22:00 Paris.
- `resupply_closes_at` = Thursday 08:59:59 Europe/Paris.
- `debrief_at` = close of the last `XNYS` session **of the week** + `debrief_delay_min`
  (default **30 min**, so the official closing price is available), and never before
  every instrument's `P_end` exists. Example: Friday 2026-12-25 is closed everywhere, so
  that week's debrief follows Thursday's US close.

Every RPC checks `now()` against these timestamps, never against `week.phase` alone
(the cron can run late).

**Reference prices** (per instrument, from its own exchange calendar):

- `P0` = official **open** of the first trading session of the week.
- `P_mid` = official **open** of the first trading session on or after Thursday.
- `P_end` = official **close** of the last trading session of the week.
- If the exchange has no session in a segment, that segment's return is 0.
- Prices are **never adjusted for dividends** (for `yfinance`: `auto_adjust=False`); the
  engine adds dividends back itself, so nothing is counted twice. Yahoo adjusts past
  prices for splits: when every reference price of a week comes from one fetch, they share
  one share basis and the split ratios are 1; `k` is only needed for prices captured
  before a split and compared with prices captured after it.
- Splits: prices are adjusted by the split ratio.
- Dividends: a cash dividend belongs to the segment in which its price drop is observed.
  A segment runs from a start price to an end price; the dividend counts when its ex-date
  session is **strictly after the start session and on or before the end session**:
  - S1 (`P0` Monday open → `P_mid` Thursday open): ex-date on Tuesday, Wednesday or
    Thursday. An ex-date on Monday is already inside `P0` and is ignored.
  - S2 (`P_mid` Thursday open → `P_end` Friday close): ex-date on Friday only (a Thursday
    ex-date is already inside `P_mid`).
  - When a holiday moves `P0` or `P_mid`, apply the same rule to the actual sessions.

**Segment returns** (in %): `r1 = ((P_mid + D1) / P0 − 1) × 100`,
`r2 = ((P_end + D2) / P_mid − 1) × 100`.

With a split of ratio `k` (new shares per old share, e.g. 2 for a 2-for-1) inside a segment,
the segment's end price and its dividend are per new share:
`r1 = ((P_mid + D1) × k1 / P0 − 1) × 100`, `r2 = ((P_end + D2) × k2 / P_mid − 1) × 100`.
A segment with a missing price returns 0 and is flagged in the breakdown. If the price
source is down on Friday night, the debrief waits 2 hours for `P_end`, then uses the
instrument's last live quote of the week instead, flagged in the debrief; with no quote at
all, the price is missing.

Scoring is additive per segment. The small difference from a compounded weekly return is
accepted: it lets every mid-week order apply cleanly to S2 only.

**Display-only daily phases** (computed from calendars, used for the live UI and the
Front Dispatch): European Assault (EU open → US open), Crossfire (US open → EU close),
US Counter-offensive (EU close → US close).

**Missing squad at lock**: the previous week's squad is redeployed if still valid (a stale
priority_target is replaced by a random Conflict Zone stock). Week 1 or invalid: a random
valid squad. Flag `auto = true`.

---

## 3. Squad

- 5 front slots + reserve. Reserve = 2 units (1 EU + 1 US); Quartermaster: 3 units with at
  least 1 EU and 1 US.
- An instrument appears at most once in a squad (front + reserve).
- Front must contain ≥2 EU and ≥2 US units.
- `veteran` region ≠ `champion` region.
- `priority_target` must be in this week's Conflict Zone.

| Slot | UI (FR) | Multiplier `m` |
|---|---|---|
| `champion` | Champion | 2.0 |
| `veteran` | Vétéran | 1.5 |
| `marksman` | Tireur d'élite | 1.0 |
| `saboteur` | Saboteur | −1.0 (short) |
| `priority_target` | Cible prioritaire | 1.2 |

**Unit coefficient** (frozen at lock for the week):
`vol12w` = sample standard deviation (n − 1) of the instrument's last 12 weekly returns
(%), computed on Friday's data. With `vol12w = 0`, `coef` is the maximum. `coef = clamp(REF_VOL / vol12w, 0.25, 2.0)` with `REF_VOL = 3.5`.

Display class (cosmetic): `vol12w < 3` Blindé · `< 5` Infanterie · `< 9` Commando ·
else Kamikaze.

**Conflict Zone** (set by the Friday market job for the next week, 8 stocks, the same for
every league): instruments with earnings next week first (by market cap, from the price
provider, stored in `instrument_weeks.market_cap`), then the largest absolute weekly moves.

**Swaps at resupply**:

- Each player may make **1 swap** (`max_swaps`), the Quartermaster **2**.
- A swap moves one reserve unit into one front slot. The outgoing unit leaves the squad
  for the week (it does not go back to the reserve). A reserve unit can be used once.
- After all of a player's swaps, the front must still satisfy every squad rule above
  (≥2 EU and ≥2 US, `veteran` region ≠ `champion` region, `priority_target` in this week's
  Conflict Zone). An invalid swap is rejected by the RPC.
- Swaps can be changed or cancelled until `resupply_closes_at`; they apply at that time.
- A Blockaded player cannot swap.

**Unit weather** (display only, computed by the Friday market job; thresholds in
`engine/config.py`). A unit can show several:

| Code | EN | FR | Condition |
|---|---|---|---|
| `on_fire` | On Fire | En feu | Previous-week return ≥ +5 % |
| `frozen` | Frozen | Surgelée | Previous-week return ≤ −5 % |
| `earnings` | Earnings this week | Résultats cette semaine | Earnings date inside the coming week |
| `roller_coaster` | Roller Coaster | Montagnes russes | At least one daily move ≥ 4 % (absolute) last week |

---

## 4. Scoring (per player, per week)

Compute in this order. Round half away from zero only where stated.

1. **Unit segment PF**: for each unit active in a segment,
   `pf_seg = r_seg × 10 × m_slot × coef × order_mod_seg`.
   Commander multipliers replace `m_slot` (§5). Orders only modify S2 (§6).
2. **Swaps**: a unit swapped out at resupply scores S1 only; the incoming reserve unit
   takes the same slot and scores S2 only.
3. **Unit weekly PF** = `round(pf_s1 + pf_s2)`, then clamp to **±150** per slot
   (a swapped slot is clamped as one slot).
4. **Elite unit**: +10 PF **[calibrate]** for each front unit (at lock) that no other
   human deployed in their front this week.
5. **Feats** (see §8).
6. **Bastion** passive.
7. **Pillage** transfers between players.
8. **Betrayal** penalty.
9. **Hunter** passive (needs every other player's score from steps 1–8).
10. `pf_total` = sum. Store a full `breakdown` JSON for the UI.

`pf_picking` = sum of steps 1–3 only (stock picking with order effects, without bonuses,
feats, passives or transfers). It is stored in the breakdown and used to compare a
player with the Drone (`rusty` badge).

### Campaign points by weekly rank (humans only; the Drone is shown, not ranked)

| Humans | 1st | 2nd | 3rd | 4th | 5th |
|---|---|---|---|---|---|
| 3 | 10 | 5 | 2 | | |
| 4 | 10 | 6 | 3 | 1 | |
| 5 | 10 | 7 | 5 | 3 | 1 |

**[calibrate]** Ties share the average of the tied ranks' points (e.g. two 2nd places with
4 humans → (6+3)/2 = 4.5 each). Final week: ×2.

**Campaign tiebreak**: most weekly 1st places, then highest cumulative PF.

---

## 5. Commanders

| Code | UI (FR) | Passive | Constraint |
|---|---|---|---|
| `bastion` | Le Bastion | Largest unit loss of the week reduced by **5 PF** (`min(loss, 5)`, on the worst slot PF after the ±150 clamp; 0 if no slot is negative) **[calibrate]** | — |
| `berserker` | Le Berserker | Champion multiplier **3.0** instead of 2.0 | Cannot play `force_field` or `tactical_retreat` |
| `prophet` | Le Prophète du déclin | Saboteur multiplier **−2.0** instead of −1.0 | — |
| `hunter` | Le Chasseur de primes | **+6 PF** per human with strictly more campaign points (before this week) whom the Hunter outscores this week (step 1–8 scores), max **+12** **[calibrate]** | — |
| `shadow` | L'Ombre | Squad, live score and S2 swap hidden from others until debrief; absent from the live leaderboard (others' live ranks are computed without the Shadow); own orders anonymous; cannot be targeted by `intel` | — |
| `technomancer` | Le Technomancien | +1 ammo per week; ammo cap 6 | — |
| `quartermaster` | L'Intendant | Reserve of 3; up to 2 swaps at resupply (others: 1) | — |

---

## 6. Ammo and orders

- **Income**: at each briefing opening, +3 ammo (Technomancer +4). Cap 5 (Technomancer 6).
  Week 1: income only.
- **Catch-up**: at briefing opening (week ≥2), humans ranked strictly in the bottom half
  of campaign standings (`rank > ceil(n/2)`) get +1 ammo.
- The cap applies to the balance after income **and** catch-up; it never lowers a balance.
- **Bounty**: the strict campaign leader (no tie) carries the Bounty. Attack orders against
  them cost 1 less (minimum 1).
- **Attack cap**: a player can receive at most **2 attack orders per week**. A third attempt
  is rejected at play time; no ammo is spent.
- Orders are validated and paid at play time by RPC and cannot be cancelled. They resolve
  when their window closes (briefing orders at `lock_at`, resupply orders at
  `resupply_closes_at`), in play-timestamp order. **Exception**: `intel` resolves
  immediately when played (see below).
- **Force field timing**: a `force_field` protects its owner from the **first attack
  order played against them after the force field's own play timestamp**. An attack played
  earlier is not blocked. A briefing force field not consumed at lock keeps protecting
  during resupply. Several force fields each block one attack, in play order.
- Own-unit maneuvers of the same player (`field_promotion`, `reversal`,
  `tactical_retreat`) apply in play-timestamp order.
- `field_promotion`, `reversal`, `tactical_retreat`: at most once per player per week.

| Code | UI (FR) | Type | Cost | Window | Effect |
|---|---|---|---|---|---|
| `orbital_strike` | Frappe orbitale | attack | 2 | resupply | Target's chosen front unit: S2 PF ×0.5 (gains and losses) |
| `pillage` | Pillage | attack | 3 | resupply | If target's S2 unit PF sum > 0: transfer `round(30%)` of it from target to attacker (details below) |
| `blockade` | Blocus | attack | 2 | briefing | Target cannot swap nor play resupply orders this week |
| `jamming` | Brouillage | attack | 1 | briefing or resupply | Target's live PF and live rank hidden (`???`) from everyone, target included, until debrief (details below) |
| `force_field` | Champ de force | defense | 1 | briefing or resupply (hidden) | Cancels the first attack received after it (by play time, see above). The attacker's ammo is lost and they are told "blocked" |
| `tactical_retreat` | Repli tactique | defense | 1 | resupply | One own front unit scores 0 on S2 |
| `field_promotion` | Promotion sur le terrain | maneuver | 2 | resupply | Swap the S2 multipliers of the champion and one other own front unit |
| `reversal` | Retournement | maneuver | 2 | resupply | Marksman multiplier becomes −1.0 for S2 |
| `intel` | Renseignement | maneuver | 1 | briefing | Resolves **immediately**: shows the attacker a one-time snapshot of the target's draft at that instant (they may still change it). Not usable on the Shadow |

Attack-type orders: `orbital_strike`, `pillage`, `blockade`, `jamming`.
Multiple `orbital_strike` on the same unit stack (×0.25).

**Pillage details**: the base is the target's S2 unit PF sum after all S2 order effects
(orbital strike, retreat, promotion, reversal) and **before** the ±150 slot clamp. Two
pillages on the same target each take `round(30%)` of the **same** base (not of what is
left). The transfer happens at step 7 and is not clamped.

**Jamming details**: jamming hides points and ranks, not prices. Unit prices and returns
(%) stay visible; a determined player could recompute a score by hand, and that is
accepted (it is a game effect, not a secret). A jammed player is listed at the bottom of
the live leaderboard as `???`, without a rank; the others' live ranks are computed
without them. The target's own per-unit live PF are also shown as `???`.

**Hidden information accepted as visible**: an attack rejected by the attack cap reveals
that the target already received 2 attacks this week.

---

## 7. Pacts

- During briefing, a player proposes a pact to another human; the other accepts or
  declines (or ignores it until lock). A player may have several pending proposals, but
  accepting one fails if either player already has an active pact this week; the other
  pending proposals of both players are then cancelled. An active pact is public and lasts
  until debrief. Max 1 active pact per player per week. It cannot be cancelled.
- **Betrayal**: any attack-type order played against your ally counts as betrayal, even if
  a force field blocks it. The attack still works (unless blocked), but the attacker gets
  **−40 PF once per week** (step 8), however many attacks, and the `traitor` badge.

---

## 8. Feats and badges

Feats (PF, step 5):

| Code | UI (FR) | PF | Condition |
|---|---|---|---|
| `total_victory` | Victoire totale | +60 | All 5 front slots end with unit PF > 0 |
| `perfect_shot` | Tir parfait | +40 | Holds, in a non-saboteur front slot, the instrument with the highest weekly return among all humans' non-saboteur front units. Ties: all holders (+40 once) |
| `resurrection` | Résurrection | +40 | Once per week: a non-saboteur front instrument with previous-week return < −6 % and this-week return > +4 % |
| `heavy_losses` | Pertes lourdes | −40 | Per non-saboteur front unit whose instrument's weekly return < −10 % |

Weekly return for feats = `((P_end + D) / P0 − 1) × 100` of the instrument, where `D`
is every dividend whose ex-date session is strictly after the `P0` session and on or
before the `P_end` session. With splits: `((P_end + D2) × k2 × k1 + D1 × k1) / P0 − 1`.
An instrument with a missing `P0` or `P_end` has no weekly return and earns no feat.

**Feats and swaps**: `perfect_shot`, `resurrection` and `heavy_losses` look at the
instruments in the front **at lock** (like Elite unit), whether or not they were swapped
out later. `total_victory` and `friendly_fire` look at the 5 front **slots** (a swapped
slot counts as one slot, §4 step 3).

Badges (computed at debrief, displayed next to the pseudo during the following week):

| Code | UI (FR) | Condition |
|---|---|---|
| `warlord` | Seigneur de guerre | Weekly rank 1 |
| `oracle` | Oracle | Saboteur unit PF ≥ +50 |
| `cannon_fodder` | Chair à canon | A long unit with previous-week return < −6 % and this-week return < −5 % |
| `friendly_fire` | Tir ami | All 5 front unit PF < 0 |
| `traitor` | Traître | Betrayed an ally this week |
| `rusty` | Rouillé | `pf_picking` (steps 1–3 only) below the Drone's score |

---

## 9. The Drone

- Enabled by default. Each week: a random valid squad, seed = hash(league_id, week).
- Scored with steps 1–3 only. No commander, no orders, no feats, not targetable.
- Shown in the weekly leaderboard with a "Drone" tag, excluded from ranks and campaign
  points. Used for the `rusty` badge (compared with each human's `pf_picking`, which is
  computed with the same steps 1–3, so the comparison is fair).
- The Drone is a league member without a user account (see ARCHITECTURE §4).

---

## 10. Front Dispatch (gazette) — FR: Communiqué du Front

Template-based text in English and French. Stored as `events` (kind `dispatch`) holding a
template key + variables; each player's client renders it in their own language.
Three editions:

1. **Monday, EU open + 10 min**: opening gap, biggest early mover, first live leader.
2. **Thursday, 09:10**: resupply recap — swaps, revealed orders (Shadow stays anonymous,
   force fields revealed only when triggered), pacts.
3. **Debrief** (at `debrief_at`, usually Friday night): weekly ranking, feats, badges,
   best and worst unit, Drone verdict.

Before debrief, a Dispatch never names a Shadow or a jammed player as live leader, never
mentions a Shadow's units or swap, and never gives a jammed player's score or rank.

Each template has variables and 3+ variants per language, picked by seed (same variant
index in both languages so friends reading in different languages see the same joke). An optional LLM rewrite can be
added later behind a feature flag (never with a key in the repo).

---

## 11. Catalogue

`data/instruments.csv` (UTF-8, LF line endings): 100 instruments (50 EU, 50 US) with
`ticker` (Yahoo format), `name`, `region`, `calendar_mic` (`exchange_calendars` code),
`currency`, `sector` (a code; labels below and in the i18n files).
All US instruments use the `XNYS` calendar. Nokia (`XHEL`) and Novo Nordisk (`XCSE`)
keep their own calendars. Validate every ticker against the price source in milestone 03
and report failures instead of silently dropping them. Market cap is not in the CSV: it
changes, so the market job stores it weekly in `instrument_weeks.market_cap`.

| `sector` code | Region | EN | FR |
|---|---|---|---|
| `luxury_fashion` | EU | Luxury & Fashion | Luxe & Mode |
| `eu_tech` | EU | Tech & Semiconductors | Tech & Semi-conducteurs |
| `industry_defense_aero` | EU | Industry, Defense & Aero | Industrie, Défense & Aéro |
| `auto_mobility` | EU | Auto & Mobility | Auto & Mobilité |
| `energy_utilities` | EU | Energy & Utilities | Énergie & Services publics |
| `banks_insurance` | EU | Banks & Insurance | Banques & Assurances |
| `health_consumer` | EU | Health & Consumer | Santé & Consommation |
| `fr_high_vol` | EU | French high-volatility | Haute volatilité France |
| `magnificent_7` | US | Magnificent 7 | Les 7 Magnifiques |
| `us_tech_ai` | US | Tech, AI & Semiconductors | Tech, IA & Semi-conducteurs |
| `apps_gaming` | US | Apps & Gaming | Applis & Jeux vidéo |
| `hype_extreme_vol` | US | Hype & Extreme volatility | Hype & Volatilité extrême |
| `consumer_brands` | US | Consumer brands | Marques grand public |
| `wall_street_payments` | US | Wall Street & Payments | Wall Street & Paiements |
| `health_energy_industry` | US | Health, Energy & Industry | Santé, Énergie & Industrie |

---

## 12. Edge cases (must have tests)

- Exchange holiday on Monday → `P0` = first open of the week; on Thursday → `P_mid` = next open.
- Friday holiday: `debrief_at` follows the last session of the week (e.g. Friday
  2026-12-25, all markets closed; Friday 2026-07-03, US closed). US holiday on Wednesday →
  `resupply_opens_at` follows Tuesday's US close. US Thanksgiving (Thursday) and its
  half-day Friday.
- DST mismatch weeks (US and EU clocks change on different Sundays).
- Dividend ex-date on the first session of a segment (ignored) and on its last session
  (counted).
- Late start: a campaign started less than 12 h before Sunday's lock begins the week after.
- Instrument with no data for a whole segment → return 0, flagged in the breakdown.
- Trading halt / delisting mid-week → last available price.
- Stock split inside a segment.
- Ex-dividend inside a segment.
- Ties in weekly score (shared campaign points) and in campaign standings.
- Player with no squad at lock (auto squad).
- Attack cap reached; force field consumed by the first attack; attack played before the
  force field (not blocked); Berserker trying to play a defense order; order on the Shadow
  with `intel`; `intel` snapshot taken before the target changes their draft; betrayal
  within a pact, including a blocked betrayal and two betrayals in one week (−40 once).
- Two pillages on the same target (same base); pillage when the target's S2 sum ≤ 0.
- Swap of a unit that was targeted by an `orbital_strike` (the strike follows the slot).
- Swap that would break a squad rule (rejected); Quartermaster making 2 swaps; a third swap
  attempt (rejected).
- Feats on a unit swapped out at resupply (still counted, front at lock).
- Jobs run twice, late, or out of order: no double scoring.

---

## 13. UI labels (EN / FR)

| Code | English | Français |
|---|---|---|
| `pf` | FP (Fantasy Points) | PF (Points Fantasy) |
| `campaign_points` | Campaign points | Points de campagne |
| `campaign` | Campaign | Campagne |
| `squad` | Squad | Escouade |
| `unit` | Unit | Unité |
| `reserve` | Reserve | Réserve |
| `champion` | Champion | Champion |
| `veteran` | Veteran | Vétéran |
| `marksman` | Marksman | Tireur d'élite |
| `saboteur` | Saboteur | Saboteur |
| `priority_target` | Priority Target | Cible prioritaire |
| `conflict_zone` | Conflict Zone | Zone de conflit |
| class armored / infantry / commando / kamikaze | Armored / Infantry / Commando / Kamikaze | Blindé / Infanterie / Commando / Kamikaze |
| `briefing` | Briefing | Briefing |
| `s1_live` / `s2_live` | Segment 1 / Segment 2 | Segment 1 / Segment 2 |
| `resupply` | Resupply | Ravitaillement |
| `debrief` | Debrief | Bilan de bataille |
| daily phases | European Assault / Crossfire / US Counter-offensive | Assaut européen / Feu croisé / Contre-offensive US |
| markets closed | Markets closed | Marchés fermés |
| unit weather | On Fire / Frozen / Earnings this week / Roller Coaster | En feu / Surgelée / Résultats cette semaine / Montagnes russes |
| sectors | see §11 | voir §11 |
| `is_final` | Final Assault | Assaut final |
| `ammo` | Ammo | Munitions |
| `order` | Order | Ordre |
| `bounty` | Bounty | La Prime |
| `pact` | Pact | Pacte |
| `drone` | Random Drone | Drone aléatoire |
| elite unit | Elite Unit | Unité d'élite |
| `bastion` | The Bastion | Le Bastion |
| `berserker` | The Berserker | Le Berserker |
| `prophet` | The Doom Prophet | Le Prophète du déclin |
| `hunter` | The Bounty Hunter | Le Chasseur de primes |
| `shadow` | The Shadow | L'Ombre |
| `technomancer` | The Technomancer | Le Technomancien |
| `quartermaster` | The Quartermaster | L'Intendant |
| `orbital_strike` | Orbital Strike | Frappe orbitale |
| `pillage` | Plunder | Pillage |
| `blockade` | Blockade | Blocus |
| `jamming` | Jamming | Brouillage |
| `force_field` | Force Field | Champ de force |
| `tactical_retreat` | Tactical Retreat | Repli tactique |
| `field_promotion` | Field Promotion | Promotion sur le terrain |
| `reversal` | Reversal | Retournement |
| `intel` | Intel | Renseignement |
| `total_victory` | Total Victory | Victoire totale |
| `perfect_shot` | Perfect Shot | Tir parfait |
| `resurrection` | Resurrection | Résurrection |
| `heavy_losses` | Heavy Losses | Pertes lourdes |
| `warlord` | Warlord | Seigneur de guerre |
| `oracle` | Oracle | Oracle |
| `cannon_fodder` | Cannon Fodder | Chair à canon |
| `friendly_fire` | Friendly Fire | Tir ami |
| `traitor` | Traitor | Traître |
| `rusty` | Rusty | Rouillé |
| dispatch | Front Dispatch | Communiqué du Front |

---

## 14. Changes in v2.1

| Topic | v2 | v2.1 |
|---|---|---|
| Rounding | "round" undefined | Half away from zero everywhere |
| Late start | Any time before Sunday 23:59 | At least 12 h before the lock, else the week after |
| Phase boundaries | Fixed "Wednesday / Friday US close" | Last `XNYS` session close (holiday-proof), debrief + 30 min |
| Dividends | "ex-date inside a segment" | Exact session rule; prices fetched unadjusted |
| Swaps | Count and validity unspecified | 1 swap (Quartermaster 2); squad rules still apply after swaps |
| Elite unit | +25 PF | +10 PF **[calibrate]** |
| `rusty` | Below the Drone | `pf_picking` (steps 1–3) below the Drone |
| `intel` | Resolved at lock (useless) | Resolves immediately, one-time snapshot |
| Force field | "first" vs "next" ambiguous | Blocks the first attack played after it |
| Pillage | Base and stacking unspecified | S2 sum after orders, before clamp; same base for each |
| Betrayal | Per attack, blocked unclear | Blocked counts; −40 PF once per week |
| Jamming / Shadow | Score hidden | Score and rank hidden; ranks computed without them |
| Feats with swaps | Unspecified | Front at lock |
| `perfect_shot` | Any front unit | Non-saboteur front units only |
| `vol12w`, ammo cap, Bastion | Unspecified details | Sample stdev; cap after catch-up; worst slot after clamp |
| Pacts | Accept or ignore | Accept, decline or ignore; several pending allowed |
| Leaving a league | Unspecified | Lobby only |
| Unit weather, sectors | French labels only, no rules | Codes, EN/FR labels, thresholds |
