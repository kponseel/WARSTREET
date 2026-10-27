// Client debug log: a ring buffer of what happened in this tab (RPC calls and their
// outcome, Realtime channel states, uncaught errors). Shown on #/debug and copyable for a
// bug report. Never holds tokens or emails: callers log codes, ids and durations only.
export type LogLevel = 'debug' | 'info' | 'warn' | 'error'

export interface LogEntry {
  ts: string
  level: LogLevel
  scope: string
  message: string
  data?: Record<string, unknown>
}

const LIMIT = 300
const DEBUG_KEY = 'debug'
const entries: LogEntry[] = []
const listeners = new Set<() => void>()

const EMAIL = /[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g
const JWT = /eyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}/g

export function scrub(text: string): string {
  return text.replace(EMAIL, '[email]').replace(JWT, '[jwt]')
}

export function logEvent(
  level: LogLevel,
  scope: string,
  message: string,
  data?: Record<string, unknown>,
): void {
  const entry: LogEntry = { ts: new Date().toISOString(), level, scope, message: scrub(message) }
  if (data) entry.data = JSON.parse(scrub(JSON.stringify(data))) as Record<string, unknown>
  entries.push(entry)
  if (entries.length > LIMIT) entries.splice(0, entries.length - LIMIT)
  if (isDebug() || level === 'error') {
    const line = `[${scope}] ${entry.message}`
    if (level === 'error') console.error(line, entry.data ?? '')
    else console.info(line, entry.data ?? '')
  }
  for (const listener of listeners) listener()
}

export function logEntries(): readonly LogEntry[] {
  return entries
}

export function clearLog(): void {
  entries.length = 0
  for (const listener of listeners) listener()
}

export function subscribeLog(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

function storage(): Storage | null {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

export function isDebug(): boolean {
  return storage()?.getItem(DEBUG_KEY) === '1'
}

export function setDebug(on: boolean): void {
  if (on) storage()?.setItem(DEBUG_KEY, '1')
  else storage()?.removeItem(DEBUG_KEY)
  for (const listener of listeners) listener()
}

/** `?debug=1` / `?debug=0` in the address turns the debug mode on or off (then removed). */
export function readDebugFlag(location: Pick<Location, 'href'>, history: Pick<History, 'replaceState'>): void {
  const url = new URL(location.href)
  const flag = url.searchParams.get('debug')
  if (flag === null) return
  setDebug(flag === '1')
  url.searchParams.delete('debug')
  history.replaceState(null, '', url.toString())
}

/** Uncaught errors and rejected promises go to the log. */
export function captureGlobalErrors(target: Window = window): void {
  target.addEventListener('error', (event) => {
    logEvent('error', 'window', event.message, { source: event.filename, line: event.lineno })
  })
  target.addEventListener('unhandledrejection', (event) => {
    const reason: unknown = event.reason
    logEvent('error', 'promise', reason instanceof Error ? reason.message : String(reason))
  })
}
