import { en, type MessageKey } from './en'
import { fr } from './fr'

export const LOCALES = ['en', 'fr'] as const
export type Locale = (typeof LOCALES)[number]

export const messages: Record<Locale, Record<MessageKey, string>> = { en, fr }

export type Vars = Record<string, string | number>

export function translate(locale: Locale, key: MessageKey, vars?: Vars): string {
  const template = messages[locale][key]
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (match, name: string) => {
    const value = vars[name]
    return value === undefined ? match : String(value)
  })
}

// fr* → French, anything else → English (CLAUDE.md conventions).
export function detectLocale(languages: readonly string[]): Locale {
  const first = languages[0]?.toLowerCase() ?? ''
  return first.startsWith('fr') ? 'fr' : 'en'
}

export function isLocale(value: unknown): value is Locale {
  return value === 'en' || value === 'fr'
}
