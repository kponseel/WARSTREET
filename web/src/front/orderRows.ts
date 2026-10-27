import type { LiveRow } from './useFront'

/** Ranked players first, then the Drone (shown, never ranked), then jammed players (???). */
export function orderRows(rows: LiveRow[], droneId: string | null): LiveRow[] {
  const ranked = rows.filter((r) => r.rank_live !== null).sort((a, b) => (a.rank_live ?? 0) - (b.rank_live ?? 0))
  const drone = rows.filter((r) => r.member_id === droneId)
  const jammed = rows.filter((r) => r.jammed)
  return [...ranked, ...drone, ...jammed]
}
