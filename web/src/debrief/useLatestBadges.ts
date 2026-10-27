import type { SupabaseClient } from '@supabase/supabase-js'
import { useEffect, useState } from 'react'
import { latestBadges, type Badge } from './data'

/** Badges of the league's last debriefed week, shown next to pseudos (GAME_RULES §8). */
export function useLatestBadges(client: SupabaseClient | null, leagueId: string): Map<string, string[]> {
  const [badges, setBadges] = useState<Map<string, string[]>>(new Map())
  useEffect(() => {
    if (!client) return
    const run = { cancelled: false }
    void client
      .from('badges')
      .select('member_id, week, code')
      .eq('league_id', leagueId)
      .then(({ data }) => {
        const rows: unknown = data ?? []
        if (!run.cancelled) setBadges(latestBadges(rows as Badge[]))
      })
    return () => {
      run.cancelled = true
    }
  }, [client, leagueId])
  return badges
}
