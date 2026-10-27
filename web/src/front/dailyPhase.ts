// The daily phase banner (GAME_RULES §2, display only): European Assault (EU open → US
// open), Crossfire (US open → EU close), US Counter-offensive (EU close → US close),
// Markets closed otherwise. Session times come from public.market_sessions, written by the
// jobs from exchange_calendars: nothing here knows market hours.

export interface Session {
  mic: string
  session: string
  open_at: string
  close_at: string
}

export type DailyPhase = 'eu' | 'crossfire' | 'us' | 'closed'

export const EU_MIC = 'XPAR' // reference exchange for "Europe" (all EU venues share its hours)
export const US_MIC = 'XNYS'

export interface PhaseNow {
  phase: DailyPhase
  /** When the phase changes next (null when no session is known ahead). */
  next: Date | null
}

interface Interval {
  phase: Exclude<DailyPhase, 'closed'>
  from: number
  to: number
}

function intervals(sessions: readonly Session[]): Interval[] {
  const byDay = new Map<string, { eu?: Session; us?: Session }>()
  for (const s of sessions) {
    if (s.mic !== EU_MIC && s.mic !== US_MIC) continue
    const day = byDay.get(s.session) ?? {}
    if (s.mic === EU_MIC) day.eu = s
    else day.us = s
    byDay.set(s.session, day)
  }
  const result: Interval[] = []
  for (const { eu, us } of byDay.values()) {
    const euOpen = eu ? Date.parse(eu.open_at) : null
    const euClose = eu ? Date.parse(eu.close_at) : null
    const usOpen = us ? Date.parse(us.open_at) : null
    const usClose = us ? Date.parse(us.close_at) : null
    if (euOpen !== null && euClose !== null && usOpen !== null && usClose !== null) {
      result.push({ phase: 'eu', from: euOpen, to: Math.min(usOpen, euClose) })
      if (usOpen < euClose) result.push({ phase: 'crossfire', from: usOpen, to: euClose })
      result.push({ phase: 'us', from: Math.max(euClose, usOpen), to: usClose })
    } else if (euOpen !== null && euClose !== null) {
      result.push({ phase: 'eu', from: euOpen, to: euClose })
    } else if (usOpen !== null && usClose !== null) {
      result.push({ phase: 'us', from: usOpen, to: usClose })
    }
  }
  return result.filter((i) => i.to > i.from).sort((a, b) => a.from - b.from)
}

export function dailyPhase(now: Date, sessions: readonly Session[]): PhaseNow {
  const t = now.getTime()
  const all = intervals(sessions)
  const current = all.find((i) => i.from <= t && t < i.to)
  if (current) {
    const following = all.find((i) => i.from >= current.to)
    const next = following && following.from === current.to ? following.from : current.to
    return { phase: current.phase, next: new Date(next) }
  }
  const upcoming = all.find((i) => i.from > t)
  return { phase: 'closed', next: upcoming ? new Date(upcoming.from) : null }
}
