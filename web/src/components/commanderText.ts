import type { GameConfig } from '../data/gameConfig'
import type { MessageKey } from '../i18n/en'
import { formatList, formatNumber } from '../lib/format'
import type { Locale, Vars } from '../i18n/translate'

type T = (key: MessageKey, vars?: Vars) => string

export interface CommanderText {
  name: string
  passive: string
  constraint: string
}

/** Name, passive and constraint of a commander, numbers read from game_config (§5). */
export function commanderText(t: T, locale: Locale, config: GameConfig, code: string): CommanderText {
  const n = (value: number) => formatNumber(locale, value)
  const mult = (value: number) => `×${n(value)}`
  const champion = config.numIn('slot_multipliers', 'champion')
  const saboteur = config.numIn('slot_multipliers', 'saboteur')
  const none = t('commander.noConstraint')
  switch (code) {
    case 'bastion':
      return {
        name: t('commander.bastion'),
        passive: t('commander.bastion.passive', { pf: n(config.num('bastion_loss_reduction')) }),
        constraint: none,
      }
    case 'berserker':
      return {
        name: t('commander.berserker'),
        passive: t('commander.berserker.passive', {
          mult: mult(config.num('berserker_champion_multiplier')),
          base: mult(champion),
        }),
        constraint: t('commander.berserker.constraint', {
          orders: formatList(
            locale,
            config.strings('berserker_forbidden_orders').map((o) => t(`order.${o}` as MessageKey)),
            'disjunction',
          ),
        }),
      }
    case 'prophet':
      return {
        name: t('commander.prophet'),
        passive: t('commander.prophet.passive', {
          mult: mult(config.num('prophet_saboteur_multiplier')),
          base: mult(saboteur),
        }),
        constraint: none,
      }
    case 'hunter':
      return {
        name: t('commander.hunter'),
        passive: t('commander.hunter.passive', {
          pf: n(config.num('hunter_bonus_per_target')),
          max: n(config.num('hunter_bonus_max')),
        }),
        constraint: none,
      }
    case 'shadow':
      return { name: t('commander.shadow'), passive: t('commander.shadow.passive'), constraint: none }
    case 'technomancer':
      return {
        name: t('commander.technomancer'),
        passive: t('commander.technomancer.passive', {
          extra: n(config.num('technomancer_extra_income')),
          cap: n(config.num('technomancer_ammo_cap')),
          baseCap: n(config.num('ammo_cap')),
        }),
        constraint: none,
      }
    case 'quartermaster':
      return {
        name: t('commander.quartermaster'),
        passive: t('commander.quartermaster.passive', {
          reserve: n(config.num('quartermaster_reserve_size')),
          swaps: n(config.num('quartermaster_max_swaps')),
          baseReserve: n(config.num('reserve_size')),
          baseSwaps: n(config.num('max_swaps')),
        }),
        constraint: none,
      }
    default:
      return { name: code, passive: '', constraint: none }
  }
}

/** Display name only (no game_config needed). */
export function commanderName(t: T, code: string | null): string {
  if (code === null) return t('commander.drone')
  return t(`commander.${code}` as MessageKey)
}
