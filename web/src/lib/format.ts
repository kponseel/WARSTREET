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

/** "Sun 8 Nov, 23:59 CET": an instant in Paris time with the zone label. */
export function formatInstant(locale: Locale, iso: string): string {
  return new Intl.DateTimeFormat(locale, {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: DISPLAY_TIME_ZONE,
    timeZoneName: 'short',
  }).format(new Date(iso))
}

/** Remaining time split for a countdown (never negative). */
export function remaining(fromMs: number, toMs: number): { days: number; hours: number; minutes: number; seconds: number } {
  let s = Math.max(0, Math.floor((toMs - fromMs) / 1000))
  const days = Math.floor(s / 86_400)
  s -= days * 86_400
  const hours = Math.floor(s / 3600)
  s -= hours * 3600
  const minutes = Math.floor(s / 60)
  return { days, hours, minutes, seconds: s - minutes * 60 }
}

export function formatSignedPercent(locale: Locale, value: number): string {
  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
    signDisplay: 'exceptZero',
  }).format(value) + ' %'
}

/** "+80", "−30", "0": a War Points amount with its sign. */
export function formatSigned(locale: Locale, value: number): string {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 1, signDisplay: 'exceptZero' }).format(value)
}
