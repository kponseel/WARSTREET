import { EXAMPLES } from '../content/examples.generated'
import type { GameConfig } from '../data/gameConfig'
import type { MessageKey } from '../i18n/en'
import type { Locale, Vars } from '../i18n/translate'
import { formatNumber, formatSigned, formatSignedPercent } from '../lib/format'

type T = (key: MessageKey, vars?: Vars) => string

export interface CommanderExample {
  summary: string
  example: string
}

/**
 * A one-line summary and a worked example per commander. The numbers come from
 * content/examples.generated.ts (computed by engine/examples.py) and from game_config:
 * the app never computes a score itself.
 */
export function commanderExample(t: T, locale: Locale, config: GameConfig, code: string): CommanderExample {
  const n = (value: number) => formatNumber(locale, value)
  const pf = (value: number) => formatSigned(locale, value)
  const move = (value: number) => formatSignedPercent(locale, value)
  const ex = EXAMPLES
  const summary = (key: string) => t(`commander.${key}.summary` as MessageKey)
  switch (code) {
    case 'bastion':
      return {
        summary: summary(code),
        example: t('commander.bastion.example', {
          unit: ex.bastionUnit,
          move: move(ex.bastionMove),
          before: pf(ex.bastionBefore),
          after: pf(ex.bastionAfter),
          max: n(config.num('bastion_loss_reduction')),
        }),
      }
    case 'berserker':
      return {
        summary: summary(code),
        example: t('commander.berserker.example', {
          unit: ex.berserkerUnit,
          move: move(ex.berserkerMove),
          before: pf(ex.berserkerBefore),
          after: pf(ex.berserkerAfter),
          downBefore: pf(ex.berserkerDownBefore),
          downAfter: pf(ex.berserkerDownAfter),
        }),
      }
    case 'prophet':
      return {
        summary: summary(code),
        example: t('commander.prophet.example', {
          unit: ex.prophetUnit,
          move: move(ex.prophetMove),
          before: pf(ex.prophetBefore),
          after: pf(ex.prophetAfter),
          upBefore: pf(ex.prophetUpBefore),
          upAfter: pf(ex.prophetUpAfter),
        }),
      }
    case 'hunter':
      return {
        summary: summary(code),
        example: t('commander.hunter.example', { both: n(ex.hunterBoth), one: n(ex.hunterOne) }),
      }
    case 'shadow':
      return { summary: summary(code), example: t('commander.shadow.example') }
    case 'technomancer':
      return {
        summary: summary(code),
        example: t('commander.technomancer.example', {
          extra: n(config.num('technomancer_extra_income')),
          baseIncome: n(config.num('ammo_income')),
          cap: n(config.num('technomancer_ammo_cap')),
          baseCap: n(config.num('ammo_cap')),
        }),
      }
    case 'quartermaster':
      return {
        summary: summary(code),
        example: t('commander.quartermaster.example', {
          out: ex.qmSwapOut,
          in: ex.qmSwapIn,
          before: pf(ex.qmBefore),
          after: pf(ex.qmAfter),
        }),
      }
    default:
      return { summary: '', example: '' }
  }
}
