import { en, type MessageKey } from './en'
import { fr } from './fr'

export const LOCALES = ['en', 'fr'] as const
export type Locale = (typeof LOCALES)[number]

// French is switched off during development (owner's decision, 2026-10-28): the app runs in
// English only and new messages are written in en.ts only. To bring French back, add 'fr'
// here; the i18n test then requires fr.ts to be complete again.
export const ENABLED_LOCALES: readonly Locale[] = ['en']

/** The locale the app actually uses: a disabled one (from a profile, storage or the browser) falls back to English. */
export function activeLocale(locale: Locale): Locale {
  return ENABLED_LOCALES.includes(locale) ? locale : 'en'
}

// fr.ts may lag behind en.ts while French is off: a missing French message shows the English one.
export const messages: Record<Locale, Partial<Record<MessageKey, string>>> = { en, fr }

export type Vars = Record<string, string | number>

export function translate(locale: Locale, key: MessageKey, vars?: Vars): string {
  const template = messages[locale][key] ?? en[key]
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
