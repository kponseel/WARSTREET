import type { SupabaseClient } from '@supabase/supabase-js'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  appUrl,
  completeLoginFromUrl,
  isValidCode,
  peekPendingPath,
  savePendingPath,
  takeLoginProblem,
  takePendingPath,
} from './auth'

function fakeClient(error: Error | null = null) {
  const exchangeCodeForSession = vi.fn().mockResolvedValue({ error })
  return { client: { auth: { exchangeCodeForSession } } as unknown as SupabaseClient, exchangeCodeForSession }
}

describe('completeLoginFromUrl', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('exchanges ?code= before the router mounts and keeps the #/ route', async () => {
    const { client, exchangeCodeForSession } = fakeClient()
    const replaceState = vi.fn()
    const result = await completeLoginFromUrl(
      client,
      { href: 'https://me.github.io/warstreet/?code=abc&x=1#/join/ABC123' },
      { replaceState },
    )
    expect(result).toBe('signed_in')
    expect(exchangeCodeForSession).toHaveBeenCalledWith('abc')
    expect(replaceState).toHaveBeenCalledWith(null, '', 'https://me.github.io/warstreet/?x=1#/join/ABC123')
  })

  it('does nothing without a code', async () => {
    const { client, exchangeCodeForSession } = fakeClient()
    const replaceState = vi.fn()
    const result = await completeLoginFromUrl(client, { href: 'https://me.github.io/w/#/' }, { replaceState })
    expect(result).toBe('none')
    expect(exchangeCodeForSession).not.toHaveBeenCalled()
    expect(replaceState).not.toHaveBeenCalled()
  })

  it('reports an expired link once on the login page', async () => {
    const { client } = fakeClient(new Error('expired'))
    const replaceState = vi.fn()
    expect(await completeLoginFromUrl(client, { href: 'https://a.b/?code=zz#/' }, { replaceState })).toBe(
      'failed',
    )
    expect(takeLoginProblem()).toBe('link_invalid')
    expect(takeLoginProblem()).toBeNull()
  })

  it('cleans an auth error from the URL', async () => {
    const replaceState = vi.fn()
    const href = 'https://a.b/?error=access_denied&error_description=Email+link+is+invalid#/'
    expect(await completeLoginFromUrl(null, { href }, { replaceState })).toBe('failed')
    expect(replaceState).toHaveBeenCalledWith(null, '', 'https://a.b/#/')
  })
})

describe('pending path', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('keeps a join link across the login round-trip, once', () => {
    savePendingPath('/join/ABC123')
    expect(peekPendingPath()).toBe('/join/ABC123')
    expect(takePendingPath()).toBe('/join/ABC123')
    expect(takePendingPath()).toBeNull()
  })

  it('never stores the login page or a foreign URL', () => {
    savePendingPath('/login')
    savePendingPath('https://evil.example/')
    expect(peekPendingPath()).toBeNull()
  })
})

describe('helpers', () => {
  it('builds the redirect URL from the app address', () => {
    expect(appUrl({ origin: 'https://me.github.io', pathname: '/warstreet/' })).toBe(
      'https://me.github.io/warstreet/',
    )
  })

  it.each([
    ['123456', true],
    ['12345', false],
    ['1234567', false],
    ['12a456', false],
  ])('code %s valid: %s', (code, valid) => {
    expect(isValidCode(code, 6)).toBe(valid)
  })
})
