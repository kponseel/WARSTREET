import type { SupabaseClient } from '@supabase/supabase-js'
import { useCallback, useEffect, useState } from 'react'
import { fetchLeague, type League, type Member } from '../data/leagues'
import {
  fetchAmmo,
  fetchIntel,
  fetchMyOrders,
  fetchMySquad,
  fetchOrderCosts,
  fetchPacts,
  type IntelSnapshot,
  type MyOrder,
  type OrderCost,
  type Pact,
} from '../data/orders'
import { fetchUnits, fetchWeeks, type Unit, type Week } from '../data/week'
import { logEvent } from '../lib/log'

export interface BriefingData {
  league: League
  me: Member
  week: Week
  units: Unit[]
  saved: { units: Record<string, number>; submittedAt: string | null; auto: boolean }
  ammo: number
  costs: OrderCost[]
  orders: MyOrder[]
  pacts: Pact[]
  intel: IntelSnapshot[]
}

export type BriefingState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'not-started'; league: League | null }
  | { status: 'ready'; data: BriefingData }

/** Everything the briefing screen shows for the current week, refreshed live. */
export function useBriefing(
  client: SupabaseClient | null,
  leagueId: string,
  userId: string,
): [BriefingState, () => void] {
  const [state, setState] = useState<BriefingState>({ status: 'loading' })
  const [version, setVersion] = useState(0)
  const refresh = useCallback(() => {
    setVersion((v) => v + 1)
  }, [])

  useEffect(() => {
    if (!client) return
    const run = { cancelled: false }
    void (async () => {
      try {
        const league = await fetchLeague(client, leagueId)
        const me = league?.league_members.find((m) => m.user_id === userId)
        const weeks = await fetchWeeks(client, leagueId)
        const week = weeks.at(-1)
        if (!league || !me || !week) {
          if (!run.cancelled) setState({ status: 'not-started', league })
          return
        }
        const [units, saved, ammo, costs, orders, pacts, intel] = await Promise.all([
          fetchUnits(client, week.week),
          fetchMySquad(client, leagueId, week.week, me.member_id),
          fetchAmmo(client, leagueId, me.member_id),
          fetchOrderCosts(client, leagueId),
          fetchMyOrders(client, leagueId, week.week),
          fetchPacts(client, leagueId, week.week),
          fetchIntel(client, leagueId, week.week),
        ])
        if (!run.cancelled) {
          setState({
            status: 'ready',
            data: { league, me, week, units, saved, ammo, costs, orders, pacts, intel },
          })
        }
      } catch (error) {
        logEvent('error', 'briefing', error instanceof Error ? error.message : String(error))
        if (!run.cancelled) setState({ status: 'error' })
      }
    })()
    return () => {
      run.cancelled = true
    }
  }, [client, leagueId, userId, version])

  useEffect(() => {
    if (!client) return
    const filter = `league_id=eq.${leagueId}`
    const channel = client
      .channel(`briefing:${leagueId}`)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'pacts', filter }, refresh)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'weeks', filter }, refresh)
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'events', filter }, refresh)
      .subscribe((status) => {
        logEvent('debug', 'realtime', `briefing ${status}`, { league: leagueId })
      })
    return () => {
      void client.removeChannel(channel)
    }
  }, [client, leagueId, refresh])

  return [state, refresh]
}
