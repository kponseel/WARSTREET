import type { SupabaseClient } from '@supabase/supabase-js'
import type { Locale } from '../i18n/translate'

// Where to go after the login round-trip (e.g. `/join/ABC123`). Kept in localStorage: the
// magic link usually opens a new tab, where sessionStorage would be empty.
const PENDING_PATH_KEY = 'pendingPath'
// A login problem to show on the login page after a redirect (expired link…).
const LOGIN_ERROR_KEY = 'loginError'

function store(): Storage | null {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

export function savePendingPath(path: string): void {
  if (!path.startsWith('/') || path.startsWith('/login')) return
  store()?.setItem(PENDING_PATH_KEY, path)
}

export function takePendingPath(): string | null {
  const s = store()
  const path = s?.getItem(PENDING_PATH_KEY) ?? null
  s?.removeItem(PENDING_PATH_KEY)
  return path
}

export function peekPendingPath(): string | null {
  return store()?.getItem(PENDING_PATH_KEY) ?? null
}

export type LoginProblem = 'link_invalid'

export function takeLoginProblem(): LoginProblem | null {
  const s = store()
  const value = s?.getItem(LOGIN_ERROR_KEY) ?? null
  s?.removeItem(LOGIN_ERROR_KEY)
  return value === 'link_invalid' ? value : null
}

// The app's own address: the magic link comes back here with ?code=…
export function appUrl(location: Pick<Location, 'origin' | 'pathname'>): string {
  return `${location.origin}${location.pathname}`
}

const AUTH_PARAMS = ['code', 'error', 'error_code', 'error_description']

/**
 * Runs before the router mounts. If the URL carries a PKCE `?code=` (or an auth error),
 * exchanges it for a session, then removes those parameters from the address bar while
 * keeping the `#/…` route. Returns what happened.
 */
export async function completeLoginFromUrl(
  client: SupabaseClient | null,
  location: Pick<Location, 'href'> = window.location,
  history: Pick<History, 'replaceState'> = window.history,
): Promise<'none' | 'signed_in' | 'failed'> {
  const url = new URL(location.href)
  const code = url.searchParams.get('code')
  const hasError = url.searchParams.has('error') || url.searchParams.has('error_description')
  if (!code && !hasError) return 'none'
  for (const name of AUTH_PARAMS) url.searchParams.delete(name)
  history.replaceState(null, '', url.toString())
  if (code && client) {
    const { error } = await client.auth.exchangeCodeForSession(code)
    if (!error) return 'signed_in'
  }
  store()?.setItem(LOGIN_ERROR_KEY, 'link_invalid')
  return 'failed'
}

export async function sendLoginEmail(
  client: SupabaseClient,
  email: string,
  locale: Locale,
  redirectTo: string,
): Promise<{ error: string | null }> {
  const { error } = await client.auth.signInWithOtp({
    email,
    options: { emailRedirectTo: redirectTo, shouldCreateUser: true, data: { locale } },
  })
  return { error: error ? (error.code ?? error.message) : null }
}

export async function verifyLoginCode(
  client: SupabaseClient,
  email: string,
  token: string,
): Promise<{ error: string | null }> {
  const { error } = await client.auth.verifyOtp({ email, token, type: 'email' })
  return { error: error ? (error.code ?? error.message) : null }
}

export function isValidCode(value: string, length: number): boolean {
  return new RegExp(`^\\d{${String(length)}}$`).test(value)
}
