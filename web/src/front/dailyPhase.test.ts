import { describe, expect, it } from 'vitest'
import { dailyPhase, type Session } from './dailyPhase'

// Tuesday 10 Nov 2026 (Paris UTC+1, New York UTC-5): EU 08:00-16:30Z, US 14:30-21:00Z.
const day = (session: string, mic: string, open: string, close: string): Session => ({
  mic,
  session,
  open_at: `${session}T${open}:00Z`,
  close_at: `${session}T${close}:00Z`,
})
const week = [
  day('2026-11-10', 'XPAR', '08:00', '16:30'),
  day('2026-11-10', 'XNYS', '14:30', '21:00'),
  day('2026-11-11', 'XPAR', '08:00', '16:30'),
  day('2026-11-11', 'XNYS', '14:30', '21:00'),
  day('2026-11-12', 'XPAR', '08:00', '16:30'), // US holiday (Thanksgiving-like)
]
const at = (iso: string) => dailyPhase(new Date(iso), week)

describe('daily phase', () => {
  it('follows EU open, US open, EU close, US close', () => {
    expect(at('2026-11-10T07:00:00Z')).toEqual({ phase: 'closed', next: new Date('2026-11-10T08:00:00Z') })
    expect(at('2026-11-10T09:00:00Z')).toEqual({ phase: 'eu', next: new Date('2026-11-10T14:30:00Z') })
    expect(at('2026-11-10T15:00:00Z')).toEqual({ phase: 'crossfire', next: new Date('2026-11-10T16:30:00Z') })
    expect(at('2026-11-10T17:00:00Z')).toEqual({ phase: 'us', next: new Date('2026-11-10T21:00:00Z') })
    expect(at('2026-11-10T22:00:00Z')).toEqual({ phase: 'closed', next: new Date('2026-11-11T08:00:00Z') })
  })

  it('handles a day with only Europe open, and the end of the week', () => {
    expect(at('2026-11-12T12:00:00Z')).toEqual({ phase: 'eu', next: new Date('2026-11-12T16:30:00Z') })
    expect(at('2026-11-12T18:00:00Z')).toEqual({ phase: 'closed', next: null })
  })
})

describe('leaderboard order', () => {
  it('puts ranked players first, then the Drone, then jammed players', async () => {
    const { orderRows } = await import('./orderRows')
    const row = (member_id: string, rank_live: number | null, jammed = false) => ({
      member_id,
      pf_live: jammed ? null : 1,
      rank_live,
      jammed,
      units: {},
      updated_at: '',
    })
    const ordered = orderRows([row('j', null, true), row('drone', null), row('b', 2), row('a', 1)], 'drone')
    expect(ordered.map((r) => r.member_id)).toEqual(['a', 'b', 'drone', 'j'])
  })
})
