import { REALTIME_SUBSCRIBE_STATES, type SupabaseClient } from '@supabase/supabase-js'
import { useCallback, useEffect, useState } from 'react'
import { logEvent } from '../lib/log'

export type LeagueStatus = 'lobby' | 'active' | 'finished'

export interface Member {
  member_id: string
  user_id: string | null
  pseudo: string
  commander: string | null
  avatar_color: string
  ready: boolean
  is_drone: boolean
  joined_at: string
}

export interface League {
  id: string
  name: string
  status: LeagueStatus
  invite_code: string
  host_id: string
  max_players: number
  campaign_weeks: number
  drone_enabled: boolean
  start_week: string | null
  league_members: Member[]
}

export interface LeaguePreview {
  league_id: string
  name: string
  status: LeagueStatus
  host_pseudo: string | null
  players: number
  max_players: number
  is_member: boolean
}

const LEAGUE_COLUMNS =
  'id, name, status, invite_code, host_id, max_players, campaign_weeks, drone_enabled, ' +
  'start_week, league_members (member_id, user_id, pseudo, commander, avatar_color, ready, ' +
  'is_drone, joined_at)'

function sortMembers(league: League): League {
  const members = [...league.league_members].sort(
    (a, b) =>
      Number(a.is_drone) - Number(b.is_drone) ||
      a.joined_at.localeCompare(b.joined_at) ||
      a.member_id.localeCompare(b.member_id),
  )
  return { ...league, league_members: members }
}

/** Leagues the player belongs to (RLS returns members' leagues only). */
export async function fetchMyLeagues(client: SupabaseClient): Promise<League[]> {
  const { data, error } = await client
    .from('leagues')
    .select(LEAGUE_COLUMNS)
    .order('created_at', { ascending: false })
  if (error) throw new Error(error.message)
  return (data as unknown as League[]).map(sortMembers)
}

export async function fetchLeague(client: SupabaseClient, id: string): Promise<League | null> {
  const { data, error } = await client
    .from('leagues')
    .select(LEAGUE_COLUMNS)
    .eq('id', id)
    .maybeSingle()
  if (error) throw new Error(error.message)
  return data ? sortMembers(data as unknown as League) : null
}

export function humans(league: League): Member[] {
  return league.league_members.filter((m) => !m.is_drone)
}

export function readyCount(league: League): number {
  return humans(league).filter((m) => m.ready).length
}

/** The start button: host only, lobby only, enough humans ready (GAME_RULES §1). */
export function canStart(league: League, userId: string, minPlayers: number): boolean {
  return league.status === 'lobby' && league.host_id === userId && readyCount(league) >= minPlayers
}

export function inviteLink(location: Pick<Location, 'origin' | 'pathname'>, code: string): string {
  return `${location.origin}${location.pathname}#/join/${code}`
}

type LoadState<T> =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; data: T; refresh: () => void }

export function useMyLeagues(client: SupabaseClient | null): LoadState<League[]> {
  const [state, setState] = useState<LoadState<League[]>>({ status: 'loading' })
  const [version, setVersion] = useState(0)
  const refresh = useCallback(() => {
    setVersion((v) => v + 1)
  }, [])
  useEffect(() => {
    if (!client) return
    let active = true
    fetchMyLeagues(client).then(
      (data) => {
        if (active) setState({ status: 'ready', data, refresh })
      },
      () => {
        if (active) setState({ status: 'error' })
      },
    )
    return () => {
      active = false
    }
  }, [client, version, refresh])
  return state
}

/**
 * One league, kept fresh with Realtime (league_members and weeks of that league; deletes
 * cannot be filtered, so any member deletion triggers a reload) and on tab focus.
 */
export function useLeagueRoom(
  client: SupabaseClient | null,
  id: string,
): LoadState<League | null> {
  const [state, setState] = useState<LoadState<League | null>>({ status: 'loading' })
  const [version, setVersion] = useState(0)
  const refresh = useCallback(() => {
    setVersion((v) => v + 1)
  }, [])

  useEffect(() => {
    if (!client) return
    let active = true
    fetchLeague(client, id).then(
      (data) => {
        if (active) setState({ status: 'ready', data, refresh })
      },
      () => {
        if (active) setState({ status: 'error' })
      },
    )
    return () => {
      active = false
    }
  }, [client, id, version, refresh])

  useEffect(() => {
    if (!client) return
    const filter = `league_id=eq.${id}`
    const channel = client
      .channel(`lobby:${id}`)
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'league_members', filter }, refresh)
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'league_members', filter }, refresh)
      .on('postgres_changes', { event: 'DELETE', schema: 'public', table: 'league_members' }, refresh)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'weeks', filter }, refresh)
      .subscribe((status, error) => {
        logEvent(status === REALTIME_SUBSCRIBE_STATES.SUBSCRIBED ? 'debug' : 'warn', 'realtime', `lobby ${status}`, {
          league: id,
          ...(error ? { error: error.message } : {}),
        })
      })
    const onVisible = () => {
      if (document.visibilityState === 'visible') refresh()
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      document.removeEventListener('visibilitychange', onVisible)
      void client.removeChannel(channel)
    }
  }, [client, id, refresh])

  return state
}
