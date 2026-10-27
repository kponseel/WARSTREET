import type { GameConfig } from '../data/gameConfig'
import type { Region, Unit } from '../data/week'
import type { MessageKey } from '../i18n/en'
import type { Vars } from '../i18n/translate'

// Mirror of the save_squad / check_front RPC rules (GAME_RULES §3), with the same error
// codes, so the player sees why a squad is invalid before saving. The RPC stays the
// authority: whatever this says, the server validates again.

export type Squad = Partial<Record<string, number>>

export interface RuleError {
  key: MessageKey
  vars?: Vars
}

export function slotKey(slot: string): MessageKey {
  return `slot.${slot}` as MessageKey
}

export function frontSlots(config: GameConfig): string[] {
  return config.strings('front_slots')
}

export function reserveSlots(config: GameConfig, commander: string | null): string[] {
  const size =
    commander === 'quartermaster' ? config.num('quartermaster_reserve_size') : config.num('reserve_size')
  return config.strings('reserve_slots').slice(0, size)
}

export function squadErrors(
  squad: Squad,
  units: ReadonlyMap<number, Unit>,
  config: GameConfig,
  commander: string | null,
): RuleError[] {
  const errors: RuleError[] = []
  const front = frontSlots(config)
  const reserve = reserveSlots(config, commander)
  const missing = [...front, ...reserve].filter((slot) => squad[slot] === undefined)
  for (const slot of missing) errors.push({ key: 'error.SQUAD_MISSING_SLOT', vars: { slot } })
  const ids = Object.values(squad).filter((id): id is number => id !== undefined)
  if (new Set(ids).size !== ids.length) errors.push({ key: 'error.SQUAD_DUPLICATE_INSTRUMENT' })
  const region = (slot: string): Region | undefined => {
    const id = squad[slot]
    return id === undefined ? undefined : units.get(id)?.region
  }
  if (missing.length === 0) {
    const frontMin = config.num('front_min_per_region')
    for (const r of ['EU', 'US'] as const) {
      const count = front.filter((slot) => region(slot) === r).length
      if (count < frontMin) {
        errors.push({ key: 'error.FRONT_NEEDS_REGION', vars: { region: r, min: frontMin, count } })
      }
    }
    const reserveMin = config.num('reserve_min_per_region')
    for (const r of ['EU', 'US'] as const) {
      if (reserve.filter((slot) => region(slot) === r).length < reserveMin) {
        errors.push({ key: 'error.RESERVE_NEEDS_REGION', vars: { region: r, min: reserveMin } })
      }
    }
  }
  errors.push(...pairRules(squad, units))
  return errors
}

function pairRules(squad: Squad, units: ReadonlyMap<number, Unit>): RuleError[] {
  const errors: RuleError[] = []
  const region = (slot: string) => {
    const id = squad[slot]
    return id === undefined ? undefined : units.get(id)?.region
  }
  const champion = region('champion')
  if (champion !== undefined && champion === region('veteran')) {
    errors.push({ key: 'error.VETERAN_SAME_REGION' })
  }
  const target = squad.priority_target
  if (target !== undefined && units.get(target)?.stats?.in_conflict_zone !== true) {
    errors.push({ key: 'error.PRIORITY_TARGET_NOT_IN_ZONE' })
  }
  return errors
}

/** The front rules alone (check_front): what a swap must keep true (GAME_RULES §3). */
export function frontErrors(
  front: Squad,
  units: ReadonlyMap<number, Unit>,
  config: GameConfig,
): RuleError[] {
  const errors: RuleError[] = []
  const min = config.num('front_min_per_region')
  for (const r of ['EU', 'US'] as const) {
    const count = frontSlots(config).filter((slot) => {
      const id = front[slot]
      return id !== undefined && units.get(id)?.region === r
    }).length
    if (count < min) errors.push({ key: 'error.FRONT_NEEDS_REGION', vars: { region: r, min, count } })
  }
  return [...errors, ...pairRules(front, units)]
}

/** A random valid squad ("Drone, suggest a squad"); null if the catalogue cannot make one. */
export function suggestSquad(
  units: readonly Unit[],
  config: GameConfig,
  commander: string | null,
  random: () => number = Math.random,
): Squad | null {
  const byId = new Map(units.map((u) => [u.id, u]))
  const pick = <T,>(items: readonly T[]): T | undefined => items[Math.floor(random() * items.length)]
  for (let attempt = 0; attempt < 50; attempt += 1) {
    const used = new Set<number>()
    const take = (filter: (u: Unit) => boolean): number | undefined => {
      const choice = pick(units.filter((u) => !used.has(u.id) && filter(u)))
      if (choice) used.add(choice.id)
      return choice?.id
    }
    const squad: Squad = {}
    squad.priority_target = take((u) => u.stats?.in_conflict_zone === true)
    const championRegion: Region = random() < 0.5 ? 'EU' : 'US'
    squad.champion = take((u) => u.region === championRegion)
    squad.veteran = take((u) => u.region !== championRegion)
    for (const slot of ['marksman', 'saboteur']) {
      const counts = { EU: 0, US: 0 }
      for (const id of Object.values(squad)) {
        const unit = id === undefined ? undefined : byId.get(id)
        if (unit) counts[unit.region] += 1
      }
      const min = config.num('front_min_per_region')
      const need: Region | null = counts.EU < min ? 'EU' : counts.US < min ? 'US' : null
      squad[slot] = take((u) => need === null || u.region === need)
    }
    reserveSlots(config, commander).forEach((slot, index) => {
      const want: Region | null = index === 0 ? 'EU' : index === 1 ? 'US' : null
      squad[slot] = take((u) => want === null || u.region === want)
    })
    if (squadErrors(squad, byId, config, commander).length === 0) return squad
  }
  return null
}
