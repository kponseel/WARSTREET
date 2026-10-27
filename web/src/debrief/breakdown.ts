// The engine's score breakdown (engine/engine/scoring.py), as stored in
// scores_final.breakdown. The app only displays it: every number comes from the jobs.

export interface SegmentDetail {
  instrument_id: number | null
  return: number | null
  multiplier: number
  coef: number
  modifier: number
  pf: number
  missing: boolean
}

export interface SlotDetail {
  pf: number
  raw: number
  clamped: boolean
  orders: string[]
  swapped_from: string | null
  s1: SegmentDetail | null
  s2: SegmentDetail | null
}

export interface Feat {
  code: string
  pf: number
  instrument_id?: number
}

export interface PillageLine {
  order_id: string
  from: string
  to: string
  base: number
  pf: number
}

export interface Breakdown {
  slots: Record<string, SlotDetail>
  pf_picking: number
  pf_total: number
  elite?: { instruments: number[]; pf: number }
  feats?: Feat[]
  bastion?: number
  pillage?: PillageLine[]
  betrayal?: number
  hunter?: { pf: number; victims: string[] }
}

/** Every scoring line of a breakdown, in the order of GAME_RULES §4 (steps 1–10). */
export interface Line {
  key: 'slots' | 'elite' | 'feat' | 'bastion' | 'pillage' | 'betrayal' | 'hunter'
  code?: string
  pf: number
}

export function lines(b: Breakdown): Line[] {
  const result: Line[] = []
  if (b.elite && b.elite.pf !== 0) result.push({ key: 'elite', pf: b.elite.pf })
  for (const feat of b.feats ?? []) result.push({ key: 'feat', code: feat.code, pf: feat.pf })
  if (b.bastion) result.push({ key: 'bastion', pf: b.bastion })
  for (const p of b.pillage ?? []) result.push({ key: 'pillage', pf: p.pf })
  if (b.betrayal) result.push({ key: 'betrayal', pf: b.betrayal })
  if (b.hunter && b.hunter.pf !== 0) result.push({ key: 'hunter', pf: b.hunter.pf })
  return result
}

export interface UnitPick {
  slot: string
  instrument_id: number | null
  pf: number
}

/** The player's best and worst slot of the week (by the slot PF the engine stored). */
export function bestAndWorst(b: Breakdown): { best: UnitPick; worst: UnitPick } | null {
  const units = Object.entries(b.slots).map(([slot, d]) => ({
    slot,
    // After a swap, the unit that ended the week in the slot.
    instrument_id: d.s2?.instrument_id ?? d.s1?.instrument_id ?? null,
    pf: d.pf,
  }))
  if (units.length === 0) return null
  const sorted = [...units].sort((a, z) => z.pf - a.pf)
  const best = sorted[0]
  const worst = sorted[sorted.length - 1]
  return best && worst ? { best, worst } : null
}
