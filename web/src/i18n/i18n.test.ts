import { describe, expect, it } from 'vitest'
import { en } from './en'
import { fr } from './fr'
import { activeLocale, detectLocale, ENABLED_LOCALES, messages, translate } from './translate'

const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()

describe('i18n key sets', () => {
  // While French is off (owner's decision during development), fr.ts may lag behind en.ts.
  // Turning French back on in ENABLED_LOCALES makes this test require every key again.
  it('has every English key in French whenever French is enabled', () => {
    const missing = Object.keys(en).filter((key) => !(key in fr))
    expect(ENABLED_LOCALES.includes('fr') ? missing : []).toEqual([])
  })

  it('has no French key that English lacks', () => {
    const extra = Object.keys(fr).filter((key) => !(key in en))
    expect(extra).toEqual([])
  })

  it('has no empty message and the same placeholders in both languages', () => {
    for (const [key, text] of Object.entries(en)) {
      const french = (fr as Record<string, string | undefined>)[key]
      expect(text.trim(), `en ${key}`).not.toBe('')
      if (french === undefined) continue
      expect(french.trim(), `fr ${key}`).not.toBe('')
      expect(placeholders(french), `placeholders of ${key}`).toEqual(placeholders(text))
    }
  })
})

describe('translate', () => {
  it('fills variables and keeps unknown ones visible', () => {
    expect(translate('en', 'home.title', { game: 'X' })).toBe('Welcome to X')
    expect(translate('fr', 'home.title', { game: 'X' })).toBe('Bienvenue sur X')
    expect(translate('en', 'home.title')).toBe(messages.en['home.title'])
  })
})

describe('enabled languages', () => {
  it('runs in English only while French is off, and falls back to English', () => {
    expect(ENABLED_LOCALES).toEqual(['en'])
    expect(activeLocale('fr')).toBe('en')
    expect(activeLocale('en')).toBe('en')
  })

  it('shows the English message when a French one is missing', () => {
    const key = 'app.tagline'
    const saved = messages.fr[key]
    Reflect.deleteProperty(messages.fr, key)
    try {
      expect(translate('fr', key)).toBe(en[key])
    } finally {
      messages.fr[key] = saved
    }
  })
})

describe('detectLocale', () => {
  it.each([
    [['fr-FR', 'en'], 'fr'],
    [['fr'], 'fr'],
    [['FR-be'], 'fr'],
    [['en-US', 'fr'], 'en'],
    [['de'], 'en'],
    [[], 'en'],
  ])('%j → %s', (languages, expected) => {
    expect(detectLocale(languages)).toBe(expected)
  })
})

describe('game terms', () => {
  // The weekly score is "War Points" (₩) and the order currency is "Credits" / "Crédits"
  // in both languages; the old names must not come back in anything a player reads.
  const OLD = /\b(FP|PF)\b|Fantasy Points|Points Fantasy|\bammo\b|\bmunitions?\b/i

  it('uses War Points and Credits in every message', async () => {
    const { rulesEn } = await import('../content/rules.en')
    const { rulesFr } = await import('../content/rules.fr')
    const texts = [...Object.values(en), ...Object.values(fr), JSON.stringify(rulesEn), JSON.stringify(rulesFr)]
    // Placeholders and ids keep their internal names ({ammo_cap}, term.ammo): only words count.
    const words = (text: string) => text.replace(/\{\w+\}/g, '').replace(/"(term|id)":"[^"]*"/g, '')
    const offending = texts.filter((text) => OLD.test(words(text)))
    expect(offending).toEqual([])
    expect(en['term.pf']).toBe('War Points (₩)')
    expect(fr['term.pf']).toBe('War Points (₩)')
  })
})
