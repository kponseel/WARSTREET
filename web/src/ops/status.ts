// The server status (public.system_status, written by every tick in jobs/tick.py).
import { GAME_CONFIG_VALUES } from '../content/gameConfig.generated'

export interface SystemStatus {
  last_tick_at: string | null
  last_tick_ok: boolean | null
  last_success_at: string | null
  consecutive_failures: number
  prices_updated_at: string | null
  dev_clock: boolean
}

export type Health = 'ok' | 'failing' | 'late' | 'unknown'

const HOUR_MS = 3_600_000
export const TICK_LATE_AFTER_MS = GAME_CONFIG_VALUES.status_tick_late_after_hours * HOUR_MS

/** One word for the status page: failing (last tick failed), late (cron stopped), ok. */
export function health(status: SystemStatus | null, nowMs: number, lateAfterMs = TICK_LATE_AFTER_MS): Health {
  if (!status?.last_tick_at) return 'unknown'
  if (status.last_tick_ok === false) return 'failing'
  if (nowMs - Date.parse(status.last_tick_at) > lateAfterMs) return 'late'
  return 'ok'
}

/** "12 minutes ago" in the reader's language (largest whole unit). */
export function ago(locale: string, iso: string, nowMs: number): string {
  const seconds = Math.round((Date.parse(iso) - nowMs) / 1000)
  const format = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['day', 86_400],
    ['hour', 3_600],
    ['minute', 60],
  ]
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return format.format(Math.trunc(seconds / size), unit)
  }
  return format.format(seconds, 'second')
}
