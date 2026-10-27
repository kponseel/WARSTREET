import type { SupabaseClient } from '@supabase/supabase-js'

export type Phase = 'briefing' | 's1_live' | 'resupply' | 's2_live' | 'debrief'
export type Region = 'EU' | 'US'

export interface Week {
  week: string
  number: number
  phase: Phase
  is_final: boolean
  lock_at: string
  resupply_opens_at: string | null
  resupply_closes_at: string
  debrief_at: string | null
}

export interface Instrument {
  id: number
  ticker: string
  name: string
  region: Region
  sector: string
  calendar_mic: string
}

export interface InstrumentWeek {
  instrument_id: number
  coef: number | null
  display_class: string | null
  prev_week_return: number | null
  in_conflict_zone: boolean
  weather: string[]
  earnings_date: string | null
}

export interface Unit extends Instrument {
  stats: InstrumentWeek | null
}

function fail(error: { message: string } | null): void {
  if (error) throw new Error(error.message)
}

const WEEK_COLUMNS =
  'week, number, phase, is_final, lock_at, resupply_opens_at, resupply_closes_at, debrief_at'

export async function fetchWeeks(client: SupabaseClient, leagueId: string): Promise<Week[]> {
  const { data, error } = await client
    .from('weeks')
    .select(WEEK_COLUMNS)
    .eq('league_id', leagueId)
    .order('week', { ascending: true })
  fail(error)
  return data as Week[]
}

let instrumentsCache: Promise<Instrument[]> | null = null

export function fetchInstruments(client: SupabaseClient): Promise<Instrument[]> {
  instrumentsCache ??= (async () => {
    const { data, error } = await client
      .from('instruments')
      .select('id, ticker, name, region, sector, calendar_mic')
      .order('ticker')
    fail(error)
    return data as Instrument[]
  })().catch((error: unknown) => {
    instrumentsCache = null
    throw error
  })
  return instrumentsCache
}

/** The catalogue of a week: every instrument with its stats (coef, class, zone, weather). */
export async function fetchUnits(client: SupabaseClient, week: string): Promise<Unit[]> {
  const [instruments, stats] = await Promise.all([
    fetchInstruments(client),
    client
      .from('instrument_weeks')
      .select(
        'instrument_id, coef, display_class, prev_week_return, in_conflict_zone, weather, earnings_date',
      )
      .eq('week', week),
  ])
  fail(stats.error)
  const byId = new Map((stats.data as InstrumentWeek[]).map((s) => [s.instrument_id, s]))
  return instruments.map((i) => ({ ...i, stats: byId.get(i.id) ?? null }))
}
