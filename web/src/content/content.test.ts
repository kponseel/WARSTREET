import { describe, expect, it } from 'vitest'
import { commanderText } from '../components/commanderText'
import { GameConfig } from '../data/gameConfig'
import { translate } from '../i18n/translate'
import { textOn } from '../lib/color'
import { fillRuleText } from './fillRuleText'
import { GAME_CONFIG_VALUES } from './gameConfig.generated'
import { rulesEn } from './rules.en'
import { rulesFr } from './rules.fr'

const config = GameConfig.fromValues(GAME_CONFIG_VALUES)
const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()

describe('rules content', () => {
  it('has the same sections and placeholders in English and French', () => {
    expect(rulesFr.sections.map((s) => s.id)).toEqual(rulesEn.sections.map((s) => s.id))
    expect(rulesFr.glossary.map((g) => g.term)).toEqual(rulesEn.glossary.map((g) => g.term))
    rulesEn.sections.forEach((section, i) => {
      const fr = rulesFr.sections[i]
      expect(fr?.paragraphs.length).toBe(section.paragraphs.length)
      section.paragraphs.forEach((p, j) => {
        expect(placeholders(fr?.paragraphs[j] ?? '')).toEqual(placeholders(p))
      })
    })
  })

  it('fills every placeholder with a game_config value', () => {
    const numbers = config.numbers()
    for (const rules of [rulesEn, rulesFr]) {
      const texts = [rules.intro, ...rules.sections.flatMap((s) => s.paragraphs)]
      for (const text of texts) {
        expect(fillRuleText('en', text, numbers)).not.toMatch(/\{\w+\}/)
      }
    }
    expect(fillRuleText('fr', '×{slot_veteran}', numbers)).toBe('×1,5')
  })
})

describe('commanders', () => {
  it('reads every number from game_config', () => {
    const t = (key: Parameters<typeof translate>[1], vars?: Record<string, string | number>) =>
      translate('en', key, vars)
    const berserker = commanderText(t, 'en', config, 'berserker')
    expect(berserker.passive).toBe(
      `Champion multiplier ×${String(config.num('berserker_champion_multiplier'))} instead of ×2.`,
    )
    expect(berserker.constraint).toBe('cannot play Force Field or Tactical Retreat.')
    for (const code of config.strings('commanders')) {
      const text = commanderText(t, 'en', config, code)
      expect(`${text.name} ${text.passive} ${text.constraint}`).not.toMatch(/\{\w+\}|undefined/)
    }
  })
})

describe('avatar letter colour', () => {
  it('stays readable (WCAG AA) on every avatar colour', () => {
    const luminance = (hex: string) => {
      const c = [1, 3, 5].map((i) => {
        const v = parseInt(hex.slice(i, i + 2), 16) / 255
        return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
      })
      return 0.2126 * (c[0] ?? 0) + 0.7152 * (c[1] ?? 0) + 0.0722 * (c[2] ?? 0)
    }
    for (const color of config.strings('avatar_colors')) {
      const [a, b] = [luminance(color), luminance(textOn(color))].sort((x, y) => y - x)
      expect(((a ?? 0) + 0.05) / ((b ?? 0) + 0.05)).toBeGreaterThanOrEqual(4.5)
    }
  })
})
