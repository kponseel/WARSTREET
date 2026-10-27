import type { SupabaseClient } from '@supabase/supabase-js'
import { useCallback, useEffect, useState } from 'react'
import { FALLBACK_POLL_MS, fetchLeague, type League, type Member } from '../data/leagues'
import { fetchInstruments, fetchWeeks, type Instrument, type Week } from '../data/week'
import { logEvent } from '../lib/log'
import type { Session } from './dailyPhase'

export interface LiveRow {
  member_id: string
  pf_live: number | null
  rank_live: number | null
  jammed: boolean
  units: Record<string, number>
  updated_at: string
}

export interface SquadUnit {
  member_id: string
  slot: string
  instrument_id: number
  active_s1: boolean
  active_s2: boolean
}

export interface LiveReturn {
  instrument_id: number
  last_price: number | null
  week_return_pct: number | null
  last_at: string | null
}

export interface FeedEvent {
  id: number
  ts: string
  kind: string
  template_key: string
  vars: Record<string, string | number>
  variant: number
}

export interface PublicOrder {
  id: string
  type: string
  member_id: string | null
  target_member_id: string | null
  target_slot: string | null
  status: 'applied' | 'blocked'
  resolved_at: string
}

export interface FrontData {
  league: League
  me: Member
  week: Week
  instruments: Map<number, Instrument>
  live: LiveRow[]
  myLive: { pf_live: number | null; units: Record<string, number> } | null
  squads: SquadUnit[]
  returns: Map<number, LiveReturn>
  sessions: Session[]
  events: FeedEvent[]
  orders: PublicOrder[]
}

export type FrontState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'not-started' }
  | { status: 'ready'; data: FrontData }

function rows<T>(result: { data: unknown; error: { message: string } | null }): T[] {
  if (result.error) throw new Error(result.error.message)
  return (result.data ?? []) as T[]
}

export async function loadFront(
  client: SupabaseClient,
  leagueId: string,
  userId: string,
): Promise<FrontData | null> {
  const [league, weeks, instruments] = await Promise.all([
    fetchLeague(client, leagueId),
    fetchWeeks(client, leagueId),
    fetchInstruments(client),
  ])
  const me = league?.league_members.find((m) => m.user_id === userId)
  const week = weeks.at(-1)
  if (!league || !me || !week) return null
  const monday = week.week
  const friday = new Date(Date.parse(`${monday}T00:00:00Z`) + 4 * 86_400_000).toISOString().slice(0, 10)
  const [live, myLive, squads, returns, sessions, events, orders] = await Promise.all([
    client
      .from('scores_live_public')
      .select('member_id, pf_live, rank_live, jammed, units, updated_at')
      .eq('league_id', leagueId)
      .eq('week', monday),
    client
      .from('scores_live')
      .select('pf_live, units')
      .eq('league_id', leagueId)
      .eq('week', monday)
      .eq('member_id', me.member_id)
      .maybeSingle(),
    client
      .from('squads_visible')
      .select('member_id, slot, instrument_id, active_s1, active_s2')
      .eq('league_id', leagueId)
      .eq('week', monday),
    client
      .from('live_returns')
      .select('instrument_id, last_price, week_return_pct, last_at')
      .eq('week', monday),
    client.from('market_sessions').select('mic, session, open_at, close_at').gte('session', monday).lte('session', friday),
    client
      .from('events')
      .select('id, ts, kind, template_key, vars, variant')
      .eq('league_id', leagueId)
      .eq('week', monday)
      .order('ts', { ascending: false })
      .limit(30),
    client
      .from('orders_public')
      .select('id, type, member_id, target_member_id, target_slot, status, resolved_at')
      .eq('league_id', leagueId)
      .eq('week', monday)
      .order('resolved_at', { ascending: false }),
  ])
  if (myLive.error) throw new Error(myLive.error.message)
  const mine: unknown = myLive.data
  return {
    league,
    me,
    week,
    instruments: new Map(instruments.map((i) => [i.id, i])),
    live: rows<LiveRow>(live),
    myLive: mine as FrontData['myLive'],
    squads: rows<SquadUnit>(squads),
    returns: new Map(rows<LiveReturn>(returns).map((r) => [r.instrument_id, r])),
    sessions: rows<Session>(sessions),
    events: rows<FeedEvent>(events),
    orders: rows<PublicOrder>(orders),
  }
}

/** The live front, refreshed by Realtime (live scores, events, weeks) and on tab focus. */
export function useFront(
  client: SupabaseClient | null,
  leagueId: string,
  userId: string,
): FrontState {
  const [state, setState] = useState<FrontState>({ status: 'loading' })
  const [version, setVersion] = useState(0)
  const refresh = useCallback(() => {
    setVersion((v) => v + 1)
  }, [])

  useEffect(() => {
    if (!client) return
    const run = { cancelled: false }
    loadFront(client, leagueId, userId).then(
      (data) => {
        if (!run.cancelled) setState(data ? { status: 'ready', data } : { status: 'not-started' })
      },
      (error: unknown) => {
        logEvent('error', 'front', error instanceof Error ? error.message : String(error))
        if (!run.cancelled) setState({ status: 'error' })
      },
    )
    return () => {
      run.cancelled = true
    }
  }, [client, leagueId, userId, version])

  useEffect(() => {
    if (!client) return
    const filter = `league_id=eq.${leagueId}`
    const channel = client
      .channel(`front:${leagueId}`)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'scores_live_public', filter }, refresh)
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'events', filter }, refresh)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'weeks', filter }, refresh)
      .subscribe((status) => {
        logEvent('debug', 'realtime', `front ${status}`, { league: leagueId })
      })
    const onVisible = () => {
      if (document.visibilityState === 'visible') refresh()
    }
    document.addEventListener('visibilitychange', onVisible)
    // Safety net: Realtime can lag or drop (mobile networks, a busy server).
    const poll = window.setInterval(onVisible, FALLBACK_POLL_MS)
    return () => {
      window.clearInterval(poll)
      document.removeEventListener('visibilitychange', onVisible)
      void client.removeChannel(channel)
    }
  }, [client, leagueId, refresh])

  return state
}
