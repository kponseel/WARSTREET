import type { Locale } from '../i18n/translate'
import { formatNumber } from '../lib/format'

/** Fills {placeholders} of the rules text with game_config numbers (unknown ones stay). */
export function fillRuleText(locale: Locale, text: string, numbers: Record<string, number>): string {
  return text.replace(/\{(\w+)\}/g, (match, name: string) => {
    const value = numbers[name]
    return value === undefined ? match : formatNumber(locale, value)
  })
}
