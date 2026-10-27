import type { SupabaseClient } from '@supabase/supabase-js'
import { useEffect, useState } from 'react'
import { fetchLeague, type League } from '../data/leagues'
import { fetchInstruments, fetchWeeks, type Instrument, type Week } from '../data/week'
import { logEvent } from '../lib/log'
import type { Breakdown } from './breakdown'

export interface FinalScore {
  member_id: string
  week: string
  pf_total: number
  pf_picking: number
  rank: number | null
  campaign_points: number
  breakdown: Breakdown
}

export interface Badge {
  member_id: string
  week: string
  code: string
}

export interface DispatchEvent {
  week: string
  template_key: string
  vars: Record<string, string | number>
  variant: number
}

export interface Standing {
  member_id: string
  campaign_points: number
  weekly_wins: number
  pf_cumulative: number
}

export interface CampaignData {
  league: League
  weeks: Week[]
  instruments: Map<number, Instrument>
  scores: FinalScore[]
  badges: Badge[]
  dispatches: DispatchEvent[]
  standings: Standing[]
  /** Weeks whose P_end of some instruments is their last live quote (provider down). */
  fallbacks: PriceFallback[]
}

export interface PriceFallback {
  instrument_id: number
  week: string
}

/** jobs/market_jobs.py FALLBACK_SOURCE */
export const FALLBACK_SOURCE = 'fallback:last_quote'

function rows<T>(result: { data: unknown; error: { message: string } | null }): T[] {
  if (result.error) throw new Error(result.error.message)
  return (result.data ?? []) as T[]
}

/** Everything final of a league: weekly scores, badges, debrief dispatches, standings. */
export async function loadCampaign(client: SupabaseClient, leagueId: string): Promise<CampaignData | null> {
  const [league, weeks, instruments, scores, badges, dispatches, standings, fallbacks] = await Promise.all([
    fetchLeague(client, leagueId),
    fetchWeeks(client, leagueId),
    fetchInstruments(client),
    client
      .from('scores_final')
      .select('member_id, week, pf_total, pf_picking, rank, campaign_points, breakdown')
      .eq('league_id', leagueId)
      .order('week'),
    client.from('badges').select('member_id, week, code').eq('league_id', leagueId),
    client
      .from('events')
      .select('week, template_key, vars, variant')
      .eq('league_id', leagueId)
      .eq('kind', 'dispatch')
      .eq('template_key', 'dispatch.debrief'),
    client
      .from('campaign_standings')
      .select('member_id, campaign_points, weekly_wins, pf_cumulative')
      .eq('league_id', leagueId),
    client.from('reference_prices').select('instrument_id, week').eq('kind', 'p_end').eq('source', FALLBACK_SOURCE),
  ])
  if (!league) return null
  return {
    league,
    weeks,
    instruments: new Map(instruments.map((i) => [i.id, i])),
    scores: rows<FinalScore>(scores),
    badges: rows<Badge>(badges),
    dispatches: rows<DispatchEvent>(dispatches),
    standings: rows<Standing>(standings),
    fallbacks: rows<PriceFallback>(fallbacks),
  }
}

export type LoadState<T> = { status: 'loading' } | { status: 'error' } | { status: 'ready'; data: T }

export function useCampaign(client: SupabaseClient | null, leagueId: string): LoadState<CampaignData | null> {
  const [state, setState] = useState<LoadState<CampaignData | null>>({ status: 'loading' })
  useEffect(() => {
    if (!client) return
    const run = { cancelled: false }
    loadCampaign(client, leagueId).then(
      (data) => {
        if (!run.cancelled) setState({ status: 'ready', data })
      },
      (error: unknown) => {
        logEvent('error', 'campaign', error instanceof Error ? error.message : String(error))
        if (!run.cancelled) setState({ status: 'error' })
      },
    )
    return () => {
      run.cancelled = true
    }
  }, [client, leagueId])
  return state
}

/** The badges of the last debriefed week, shown next to pseudos the following week. */
export function latestBadges(badges: readonly Badge[]): Map<string, string[]> {
  const last = badges.reduce<string>((max, b) => (b.week > max ? b.week : max), '')
  const result = new Map<string, string[]>()
  for (const b of badges) {
    if (b.week !== last) continue
    result.set(b.member_id, [...(result.get(b.member_id) ?? []), b.code])
  }
  return result
}

/** Standings in the order of GAME_RULES §4 (points, then weekly wins, then cumulative PF). */
export function sortStandings(standings: readonly Standing[]): Standing[] {
  return [...standings].sort(
    (a, b) =>
      b.campaign_points - a.campaign_points ||
      b.weekly_wins - a.weekly_wins ||
      b.pf_cumulative - a.pf_cumulative,
  )
}
