import { describe, expect, it } from 'vitest'
import { bestAndWorst } from './breakdown'
import { latestBadges, sortStandings } from './data'

describe('campaign data', () => {
  it('keeps the badges of the last debriefed week only', () => {
    const badges = latestBadges([
      { member_id: 'a', week: '2026-11-02', code: 'warlord' },
      { member_id: 'a', week: '2026-11-09', code: 'rusty' },
      { member_id: 'b', week: '2026-11-09', code: 'warlord' },
      { member_id: 'b', week: '2026-11-09', code: 'oracle' },
    ])
    expect(Object.fromEntries(badges)).toEqual({
      a: ['rusty'],
      b: ['warlord', 'oracle'],
    })
  })

  it('orders standings by points, then weekly wins, then cumulative FP (GAME_RULES §4)', () => {
    const order = sortStandings([
      {
        member_id: 'a',
        campaign_points: 20,
        weekly_wins: 1,
        pf_cumulative: 300,
      },
      {
        member_id: 'b',
        campaign_points: 20,
        weekly_wins: 2,
        pf_cumulative: 100,
      },
      {
        member_id: 'c',
        campaign_points: 20,
        weekly_wins: 1,
        pf_cumulative: 400,
      },
      { member_id: 'd', campaign_points: 25, weekly_wins: 0, pf_cumulative: 0 },
    ]).map((s) => s.member_id)
    expect(order).toEqual(['d', 'b', 'c', 'a'])
  })
})

describe('best and worst unit', () => {
  const segment = (id: number, pf: number) => ({
    instrument_id: id,
    return: 1,
    multiplier: 1,
    coef: 1,
    modifier: 1,
    pf,
    missing: false,
  })
  it('picks the slots with the highest and lowest stored PF, after a swap the new unit', () => {
    const result = bestAndWorst({
      pf_picking: 0,
      pf_total: 0,
      slots: {
        champion: {
          pf: -8,
          raw: -8,
          clamped: false,
          orders: [],
          swapped_from: null,
          s1: segment(1, -8),
          s2: null,
        },
        marksman: {
          pf: 12,
          raw: 12,
          clamped: false,
          orders: [],
          swapped_from: 'x',
          s1: segment(2, 4),
          s2: segment(3, 8),
        },
        veteran: {
          pf: 3,
          raw: 3,
          clamped: false,
          orders: [],
          swapped_from: null,
          s1: segment(4, 3),
          s2: null,
        },
      },
    })
    expect(result).toEqual({
      best: { slot: 'marksman', instrument_id: 3, pf: 12 },
      worst: { slot: 'champion', instrument_id: 1, pf: -8 },
    })
  })
  it('returns null without slots', () => {
    expect(bestAndWorst({ pf_picking: 0, pf_total: 0, slots: {} })).toBeNull()
  })
})
