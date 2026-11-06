import type { GameConfig } from '../data/gameConfig'
import type { MessageKey } from '../i18n/en'
import type { Vars } from '../i18n/translate'

type T = (key: MessageKey, vars?: Vars) => string

/** What an order does, with its numbers from game_config (Plunder's share as a percentage). */
export function orderDescription(t: T, config: GameConfig, type: string): string {
  return t(`order.${type}.desc` as MessageKey, { share: config.numbers().pillage_share_pct ?? '' })
}
