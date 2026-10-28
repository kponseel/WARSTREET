import { describe, expect, it } from 'vitest'
import { en } from './en'
import { fr } from './fr'
import { detectLocale, messages, translate } from './translate'

const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()

describe('i18n key sets', () => {
  it('has every English key in French', () => {
    const missing = Object.keys(en).filter((key) => !(key in fr))
    expect(missing).toEqual([])
  })

  it('has no French key that English lacks', () => {
    const extra = Object.keys(fr).filter((key) => !(key in en))
    expect(extra).toEqual([])
  })

  it('has no empty message and the same placeholders in both languages', () => {
    for (const [key, text] of Object.entries(en)) {
      const french = (fr as Record<string, string>)[key] ?? ''
      expect(text.trim(), `en ${key}`).not.toBe('')
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
