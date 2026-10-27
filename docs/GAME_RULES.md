# GAME_RULES.md — engine specification (rules v2, 3 to 5 players)

This document is the contract for `engine/`. Every rule has a code name (used in code and
the database). UI labels in English and French are listed in §13; the French labels shown
in tables below are for reference. All numeric values are defaults from
`engine/config.py` and must stay tunable.

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
  briefing window is still open at start time (start before Sunday 23:59 Paris → the coming
  Monday; otherwise the Monday after). Commanders are locked at start.
- **End**: after the debrief of the last week → `finished`, final standings frozen.

---

## 2. The week (all times Europe/Paris for display; stored in UTC)

Phases (`week.phase`): `briefing` → `s1_live` → `resupply` → `s2_live` → `debrief`.

| Phase | Window | What players can do |
|---|---|---|
| `briefing` | Previous debrief (Fri ~22:15) → **Sunday 23:59:59** | Build squad, briefing orders, pacts |
| `s1_live` | Lock → Wednesday US close + 5 min | Watch |
| `resupply` | Wednesday US close + 5 min → **Thursday 08:59:59** | Swap from reserve, resupply orders |
| `s2_live` | Thursday 09:00 → Friday US close + 5 min | Watch |
| `debrief` | Friday US close + 5 min → next briefing | Scoring, ranks, feats, badges, Front Dispatch |

Week 1's briefing opens at league start.

**Reference prices** (per instrument, from its own exchange calendar):

- `P0` = official **open** of the first trading session of the week.
- `P_mid` = official **open** of the first trading session on or after Thursday.
- `P_end` = official **close** of the last trading session of the week.
- If the exchange has no session in a segment, that segment's return is 0.
- Splits: prices are adjusted by the split ratio. Dividends: a cash dividend whose
  ex-date falls inside a segment is added back to that segment's end price.

**Segment returns** (in %): `r1 = ((P_mid + D1) / P0 − 1) × 100`,
`r2 = ((P_end + D2) / P_mid − 1) × 100`.

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
`vol12w` = standard deviation of the instrument's last 12 weekly returns (%), computed on
Friday's data. `coef = clamp(REF_VOL / vol12w, 0.25, 2.0)` with `REF_VOL = 3.5`.

Display class (cosmetic): `vol12w < 3` Blindé · `< 5` Infanterie · `< 9` Commando ·
else Kamikaze.

**Conflict Zone** (set by the Friday job for the next week, 8 stocks): instruments with
earnings next week first (by market cap), then the largest absolute weekly moves.

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
4. **Elite unit**: +25 PF for each front unit (at lock) that no other human deployed in
   their front this week.
5. **Feats** (see §8).
6. **Bastion** passive.
7. **Pillage** transfers between players.
8. **Betrayal** penalty.
9. **Hunter** passive (needs every other player's score from steps 1–8).
10. `pf_total` = sum. Store a full `breakdown` JSON for the UI.

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
| `bastion` | Le Bastion | Largest unit loss of the week reduced by **5 PF** (`min(loss, 5)`) **[calibrate]** | — |
| `berserker` | Le Berserker | Champion multiplier **3.0** instead of 2.0 | Cannot play `force_field` or `tactical_retreat` |
| `prophet` | Le Prophète du déclin | Saboteur multiplier **−2.0** instead of −1.0 | — |
| `hunter` | Le Chasseur de primes | **+6 PF** per human with strictly more campaign points (before this week) whom the Hunter outscores this week (step 1–8 scores), max **+12** **[calibrate]** | — |
| `shadow` | L'Ombre | Squad, live score and S2 swap hidden from others until debrief; own orders anonymous; cannot be targeted by `intel` | — |
| `technomancer` | Le Technomancien | +1 ammo per week; ammo cap 6 | — |
| `quartermaster` | L'Intendant | Reserve of 3; up to 2 swaps at resupply | — |

---

## 6. Ammo and orders

- **Income**: at each briefing opening, +3 ammo (Technomancer +4). Cap 5 (Technomancer 6).
  Week 1: income only.
- **Catch-up**: at briefing opening (week ≥2), humans ranked strictly in the bottom half
  of campaign standings (`rank > ceil(n/2)`) get +1 ammo.
- **Bounty**: the strict campaign leader (no tie) carries the Bounty. Attack orders against
  them cost 1 less (minimum 1).
- **Attack cap**: a player can receive at most **2 attack orders per week**. A third attempt
  is rejected at play time; no ammo is spent.
- Orders are validated and paid at play time by RPC. They resolve when their window
  closes (briefing orders at lock, resupply orders at Thursday 08:59:59), in this order:
  `force_field` first, then the rest by play timestamp.
- `field_promotion`, `reversal`, `tactical_retreat`: at most once per player per week.

| Code | UI (FR) | Type | Cost | Window | Effect |
|---|---|---|---|---|---|
| `orbital_strike` | Frappe orbitale | attack | 2 | resupply | Target's chosen front unit: S2 PF ×0.5 (gains and losses) |
| `pillage` | Pillage | attack | 3 | resupply | If target's S2 unit PF sum > 0: transfer `round(30%)` of it from target to attacker |
| `blockade` | Blocus | attack | 2 | briefing | Target cannot swap nor play resupply orders this week |
| `jamming` | Brouillage | attack | 1 | briefing or resupply | Target's live score shown as `???` to everyone (target included) until debrief |
| `force_field` | Champ de force | defense | 1 | briefing or resupply (hidden) | Cancels the next attack received this week (by play time). The attacker's ammo is lost and they are told "bloqué" |
| `tactical_retreat` | Repli tactique | defense | 1 | resupply | One own front unit scores 0 on S2 |
| `field_promotion` | Promotion sur le terrain | maneuver | 2 | resupply | Swap the S2 multipliers of the champion and one other own front unit |
| `reversal` | Retournement | maneuver | 2 | resupply | Marksman multiplier becomes −1.0 for S2 |
| `intel` | Renseignement | maneuver | 1 | briefing | Reveals the target's current draft (they may still change it). Not usable on the Shadow |

Attack-type orders: `orbital_strike`, `pillage`, `blockade`, `jamming`.
Multiple `orbital_strike` on the same unit stack (×0.25).

---

## 7. Pacts

- During briefing, a player proposes a pact to another human; the other accepts or ignores.
  An active pact is public and lasts until debrief. Max 1 pact per player per week.
  It cannot be cancelled.
- **Betrayal**: an attack order against your ally still works, but the attacker gets
  −40 PF (step 8) and the `traitre` badge next week.

---

## 8. Feats and badges

Feats (PF, step 5):

| Code | UI (FR) | PF | Condition |
|---|---|---|---|
| `total_victory` | Victoire totale | +60 | All 5 front slots end with unit PF > 0 |
| `perfect_shot` | Tir parfait | +40 | Holds (front) the instrument with the highest weekly return among all humans' front units. Ties: all holders |
| `resurrection` | Résurrection | +40 | Once per week: a non-saboteur front instrument with previous-week return < −6 % and this-week return > +4 % |
| `heavy_losses` | Pertes lourdes | −40 | Per non-saboteur front unit whose instrument's weekly return < −10 % |

Weekly return for feats = `((P_end + D) / P0 − 1) × 100` of the instrument.

Badges (computed at debrief, displayed next to the pseudo during the following week):

| Code | UI (FR) | Condition |
|---|---|---|
| `warlord` | Seigneur de guerre | Weekly rank 1 |
| `oracle` | Oracle | Saboteur unit PF ≥ +50 |
| `cannon_fodder` | Chair à canon | A long unit with previous-week return < −6 % and this-week return < −5 % |
| `friendly_fire` | Tir ami | All 5 front unit PF < 0 |
| `traitor` | Traître | Betrayed an ally this week |
| `rusty` | Rouillé | Finished below the Drone |

---

## 9. The Drone

- Enabled by default. Each week: a random valid squad, seed = hash(league_id, week).
- Scored with steps 1–3 only. No commander, no orders, no feats, not targetable.
- Shown in the weekly leaderboard with a "Drone" tag, excluded from ranks and campaign
  points. Used for the `rusty` badge.

---

## 10. Front Dispatch (gazette) — FR: Communiqué du Front

Template-based text in English and French. Stored as `events` (kind `dispatch`) holding a
template key + variables; each player's client renders it in their own language.
Three editions:

1. **Monday, EU open + 10 min**: opening gap, biggest early mover, first live leader.
2. **Thursday, 09:10**: resupply recap — swaps, revealed orders (Shadow stays anonymous,
   force fields revealed only when triggered), pacts.
3. **Friday debrief**: weekly ranking, feats, badges, best and worst unit, Drone verdict.

Each template has variables and 3+ variants per language, picked by seed (same variant
index in both languages so friends reading in different languages see the same joke). An optional LLM rewrite can be
added later behind a feature flag (never with a key in the repo).

---

## 11. Catalogue

`data/instruments.csv`: 100 instruments (50 EU, 50 US) with `ticker` (Yahoo format),
`region`, `calendar_mic` (`exchange_calendars` code), `currency`, `sector`.
All US instruments use the `XNYS` calendar. Nokia (`XHEL`) and Novo Nordisk (`XCSE`)
keep their own calendars. Validate every ticker against the price source in milestone 03
and report failures instead of silently dropping them.

---

## 12. Edge cases (must have tests)

- Exchange holiday on Monday → `P0` = first open of the week; on Thursday → `P_mid` = next open.
- DST mismatch weeks (US and EU clocks change on different Sundays).
- Instrument with no data for a whole segment → return 0, flagged in the breakdown.
- Trading halt / delisting mid-week → last available price.
- Stock split inside a segment.
- Ex-dividend inside a segment.
- Ties in weekly score (shared campaign points) and in campaign standings.
- Player with no squad at lock (auto squad).
- Attack cap reached; force field consumed by the first attack; Berserker trying to play a
  defense order; order on the Shadow with `intel`; betrayal within a pact.
- Swap of a unit that was targeted by an `orbital_strike` (the strike follows the slot).
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
