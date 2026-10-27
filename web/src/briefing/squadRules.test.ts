import { describe, expect, it } from 'vitest'
import { GAME_CONFIG_VALUES } from '../content/gameConfig.generated'
import { GameConfig } from '../data/gameConfig'
import type { Region, Unit } from '../data/week'
import { filterUnits, NO_FILTERS } from './filters'
import { reserveSlots, squadErrors, suggestSquad, type Squad } from './squadRules'

const config = GameConfig.fromValues(GAME_CONFIG_VALUES)

function unit(id: number, region: Region, zone = false, sector = 'x'): Unit {
  return {
    id,
    ticker: `T${String(id)}`,
    name: `Name ${String(id)}`,
    region,
    sector,
    calendar_mic: region === 'EU' ? 'XPAR' : 'XNYS',
    stats: {
      instrument_id: id,
      coef: 1,
      display_class: id % 2 ? 'armored' : 'kamikaze',
      prev_week_return: 0,
      in_conflict_zone: zone,
      weather: [],
      earnings_date: null,
    },
  }
}

// 1-10 EU, 11-20 US; 1 and 11 in the Conflict Zone.
const units = [
  ...Array.from({ length: 10 }, (_, i) => unit(i + 1, 'EU', i === 0)),
  ...Array.from({ length: 10 }, (_, i) => unit(i + 11, 'US', i === 0)),
]
const byId = new Map(units.map((u) => [u.id, u]))
const valid: Squad = {
  champion: 2,
  veteran: 12,
  marksman: 3,
  saboteur: 13,
  priority_target: 11,
  reserve_1: 4,
  reserve_2: 14,
}
const codes = (squad: Squad, commander: string | null = 'bastion') =>
  squadErrors(squad, byId, config, commander).map((e) => e.key)

describe('squad rules (mirror of save_squad)', () => {
  it('accepts a valid squad', () => {
    expect(codes(valid)).toEqual([])
  })

  it('reports each broken rule with the RPC error code', () => {
    expect(codes({ ...valid, veteran: 5 })).toEqual(['error.VETERAN_SAME_REGION'])
    expect(codes({ ...valid, champion: 15 }).sort()).toEqual([
      'error.FRONT_NEEDS_REGION',
      'error.VETERAN_SAME_REGION',
    ])
    expect(codes({ ...valid, priority_target: 15 })).toEqual(['error.PRIORITY_TARGET_NOT_IN_ZONE'])
    expect(codes({ ...valid, reserve_2: 6 })).toEqual(['error.RESERVE_NEEDS_REGION'])
    expect(codes({ ...valid, reserve_1: 2 })).toContain('error.SQUAD_DUPLICATE_INSTRUMENT')
    const partial = Object.fromEntries(Object.entries(valid).filter(([slot]) => slot !== 'saboteur'))
    expect(codes(partial)).toEqual(['error.SQUAD_MISSING_SLOT'])
  })

  it('gives the Quartermaster a third reserve slot', () => {
    expect(reserveSlots(config, 'quartermaster')).toHaveLength(3)
    expect(codes(valid, 'quartermaster')).toEqual(['error.SQUAD_MISSING_SLOT'])
  })

  it('suggests only valid squads', () => {
    let seed = 1
    const random = () => {
      seed = (seed * 16807) % 2147483647
      return seed / 2147483647
    }
    for (const commander of ['bastion', 'quartermaster']) {
      for (let i = 0; i < 20; i += 1) {
        const squad = suggestSquad(units, config, commander, random)
        expect(squad).not.toBeNull()
        expect(squadErrors(squad ?? {}, byId, config, commander)).toEqual([])
      }
    }
  })
})

describe('catalogue filters', () => {
  it('combines search, region, class and Conflict Zone', () => {
    expect(filterUnits(units, { ...NO_FILTERS, region: 'US' })).toHaveLength(10)
    expect(filterUnits(units, { ...NO_FILTERS, zoneOnly: true }).map((u) => u.id)).toEqual([1, 11])
    expect(filterUnits(units, { ...NO_FILTERS, search: 't12' }).map((u) => u.id)).toEqual([12])
    expect(filterUnits(units, { ...NO_FILTERS, displayClass: 'armored', region: 'EU' })).toHaveLength(5)
  })
})
