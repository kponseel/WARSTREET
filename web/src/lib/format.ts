import type { Locale } from '../i18n/translate'

// Numbers and dates for the active locale (CLAUDE.md conventions). Times in Europe/Paris.
export const DISPLAY_TIME_ZONE = 'Europe/Paris'

export function formatNumber(locale: Locale, value: number, maxDigits = 1): string {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: maxDigits }).format(value)
}

/** A calendar date stored as `YYYY-MM-DD` (e.g. a week's Monday). */
export function formatDay(locale: Locale, isoDate: string): string {
  return new Intl.DateTimeFormat(locale, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    timeZone: DISPLAY_TIME_ZONE,
  }).format(new Date(`${isoDate}T12:00:00Z`))
}

export function formatList(
  locale: Locale,
  items: string[],
  type: 'conjunction' | 'disjunction' = 'conjunction',
): string {
  return new Intl.ListFormat(locale, { style: 'long', type }).format(items)
}
