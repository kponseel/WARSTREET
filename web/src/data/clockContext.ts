import { createContext, useContext, useSyncExternalStore } from 'react'

export interface ClockValue {
  /** Server time minus device time, in ms (0 until the first answer). */
  offsetMs: number
  /** True when the database runs on a simulated clock (local dev mode). */
  devClock: boolean
  /** True once the server clock has answered (or failed): screens can trust `useNow`. */
  synced: boolean
}

export const ClockContext = createContext<ClockValue>({ offsetMs: 0, devClock: false, synced: true })

export function useClock(): ClockValue {
  return useContext(ClockContext)
}

function subscribe(everyMs: number) {
  return (onChange: () => void) => {
    const timer = window.setInterval(onChange, everyMs)
    return () => {
      window.clearInterval(timer)
    }
  }
}

const subscriptions = new Map<number, (onChange: () => void) => () => void>()

/**
 * The game's "now" (the server clock), refreshed every `everyMs`. A new server offset
 * applies at once (no waiting for the next tick).
 */
export function useNow(everyMs = 1000): Date {
  const { offsetMs } = useClock()
  let sub = subscriptions.get(everyMs)
  if (!sub) {
    sub = subscribe(everyMs)
    subscriptions.set(everyMs, sub)
  }
  const deviceMs = useSyncExternalStore(sub, () => Math.floor(Date.now() / everyMs) * everyMs)
  return new Date(deviceMs + offsetMs)
}
