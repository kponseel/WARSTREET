import { describe, expect, it } from 'vitest'
import { ago, health, type SystemStatus } from './status'

const base: SystemStatus = {
  last_tick_at: '2026-11-13T21:30:00Z',
  last_tick_ok: true,
  last_success_at: '2026-11-13T21:30:00Z',
  consecutive_failures: 0,
  prices_updated_at: '2026-11-13T21:35:00Z',
  dev_clock: false,
}
const at = (iso: string) => Date.parse(iso)

describe('status page', () => {
  it('reads the last tick: ok, failing, late or unknown', () => {
    const hour = 3_600_000
    expect(health(base, at('2026-11-13T21:45:00Z'), 8 * hour)).toBe('ok')
    expect(health({ ...base, last_tick_ok: false, consecutive_failures: 2 }, at('2026-11-13T21:45:00Z'))).toBe(
      'failing',
    )
    expect(health(base, at('2026-11-14T06:00:00Z'), 8 * hour)).toBe('late')
    expect(health(null, at('2026-11-13T21:45:00Z'))).toBe('unknown')
    expect(health({ ...base, last_tick_at: null }, at('2026-11-13T21:45:00Z'))).toBe('unknown')
  })

  it('says how long ago, in the reader language', () => {
    const now = at('2026-11-13T21:42:00Z')
    expect(ago('en', '2026-11-13T21:30:00Z', now)).toBe('12 minutes ago')
    expect(ago('fr', '2026-11-13T21:30:00Z', now)).toBe('il y a 12 minutes')
    expect(ago('en', '2026-11-12T21:30:00Z', now)).toBe('yesterday')
    expect(ago('en', '2026-11-13T21:41:30Z', now)).toBe('30 seconds ago')
  })
})
