import { beforeEach, describe, expect, it, vi } from 'vitest'
import { clearLog, isDebug, logEntries, logEvent, readDebugFlag, scrub, subscribeLog } from './log'

describe('client debug log', () => {
  beforeEach(() => {
    clearLog()
    window.localStorage.clear()
  })

  it('never keeps an email or a token', () => {
    // A made-up token with the shape of a JWT.
    const fakeJwt = ['{"fake":"header"}', '{"fake":"payload"}', 'not-a-real-signature']
      .map((part) => btoa(part).replace(/=+$/, ''))
      .join('.')
    logEvent('warn', 'rpc', 'join refused for player@example.com', { jwt: fakeJwt })
    const [entry] = logEntries()
    expect(entry?.message).toBe('join refused for [email]')
    expect(entry?.data).toEqual({ jwt: '[jwt]' })
    expect(scrub('a.b+c@d.co.uk')).toBe('[email]')
  })

  it('keeps the last 300 entries and notifies listeners', () => {
    const listener = vi.fn()
    const unsubscribe = subscribeLog(listener)
    for (let i = 0; i < 310; i += 1) logEvent('debug', 'test', `line ${String(i)}`)
    unsubscribe()
    expect(logEntries()).toHaveLength(300)
    expect(logEntries()[0]?.message).toBe('line 10')
    expect(listener).toHaveBeenCalledTimes(310)
  })

  it('turns debug mode on and off from the address, then cleans it', () => {
    const replaceState = vi.fn()
    readDebugFlag({ href: 'https://a.b/w/?debug=1#/l/1/lobby' }, { replaceState })
    expect(isDebug()).toBe(true)
    expect(replaceState).toHaveBeenCalledWith(null, '', 'https://a.b/w/#/l/1/lobby')
    readDebugFlag({ href: 'https://a.b/w/?debug=0#/' }, { replaceState })
    expect(isDebug()).toBe(false)
  })
})
