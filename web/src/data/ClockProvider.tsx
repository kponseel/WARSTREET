import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useAuth } from '../auth/context'
import { callRpc } from '../lib/rpc'
import { logEvent } from '../lib/log'
import { ClockContext, type ClockValue } from './clockContext'

const RESYNC_MS = 5 * 60_000
const DEV_RESYNC_MS = 20_000 // a simulated clock jumps when the dev tools advance it

/**
 * Countdowns use the server clock (public.server_time(), which is also the clock of every
 * deadline check), never the device clock: a phone set five minutes off still sees the
 * right lock countdown, and a local database in dev mode shows its simulated time.
 */
export function ClockProvider({ children }: { children: ReactNode }) {
  const { client, session } = useAuth()
  const [value, setValue] = useState<ClockValue>({ offsetMs: 0, devClock: false, synced: false })
  const signedIn = session !== null

  useEffect(() => {
    if (!client || !signedIn) return
    const run = { cancelled: false }
    const sync = async () => {
      try {
        const sent = Date.now()
        const server = await callRpc<string>(client, 'server_time')
        const received = Date.now()
        const offsetMs = new Date(server).getTime() - (sent + received) / 2
        const { data } = await client.from('system_status').select('dev_clock').maybeSingle()
        const devClock = (data as { dev_clock?: boolean } | null)?.dev_clock === true
        if (run.cancelled) return
        setValue({ offsetMs: Math.abs(offsetMs) < 1000 ? 0 : offsetMs, devClock, synced: true })
        logEvent('debug', 'clock', 'server time synced', { offsetMs: Math.round(offsetMs), devClock })
      } catch {
        logEvent('warn', 'clock', 'server time unavailable, using the device clock')
        if (!run.cancelled) setValue((v) => ({ ...v, synced: true }))
      }
    }
    void sync()
    const timer = window.setInterval(() => void sync(), value.devClock ? DEV_RESYNC_MS : RESYNC_MS)
    return () => {
      run.cancelled = true
      window.clearInterval(timer)
    }
  }, [client, signedIn, value.devClock])

  const memo = useMemo(() => value, [value])
  return <ClockContext value={memo}>{children}</ClockContext>
}
