import type { SupabaseClient } from '@supabase/supabase-js'
import { callRpc } from '../lib/rpc'

export type OrderWindow = 'briefing' | 'resupply'
export type OrderStatus = 'pending' | 'applied' | 'blocked' | 'rejected'

export interface OrderCost {
  order_window: OrderWindow
  type: string
  target_member_id: string | null
  cost: number
  target_has_bounty: boolean
}

export interface MyOrder {
  id: string
  type: string
  target_member_id: string | null
  target_slot: string | null
  order_window: OrderWindow
  cost: number
  status: OrderStatus
  created_at: string
}

export interface Pact {
  id: string
  proposer_member_id: string
  partner_member_id: string
  status: 'proposed' | 'active' | 'declined' | 'cancelled'
  created_at: string
}

export interface IntelSnapshot {
  target_member_id: string
  units: Record<string, string>
  taken_at: string
}

function fail(error: { message: string } | null): void {
  if (error) throw new Error(error.message)
}

export function fetchOrderCosts(client: SupabaseClient, leagueId: string): Promise<OrderCost[]> {
  return callRpc<OrderCost[]>(client, 'order_costs', { p_league: leagueId })
}

export async function fetchMyOrders(
  client: SupabaseClient,
  leagueId: string,
  week: string,
): Promise<MyOrder[]> {
  const { data, error } = await client
    .from('orders')
    .select('id, type, target_member_id, target_slot, order_window, cost, status, created_at')
    .eq('league_id', leagueId)
    .eq('week', week)
    .order('created_at')
  fail(error)
  return data as MyOrder[]
}

export async function fetchAmmo(client: SupabaseClient, leagueId: string, memberId: string): Promise<number> {
  const { data, error } = await client
    .from('ammo_balance')
    .select('balance')
    .eq('league_id', leagueId)
    .eq('member_id', memberId)
    .maybeSingle()
  fail(error)
  const row: unknown = data
  return (row as { balance: number } | null)?.balance ?? 0
}

export async function fetchPacts(client: SupabaseClient, leagueId: string, week: string): Promise<Pact[]> {
  const { data, error } = await client
    .from('pacts')
    .select('id, proposer_member_id, partner_member_id, status, created_at')
    .eq('league_id', leagueId)
    .eq('week', week)
    .order('created_at')
  fail(error)
  return data as Pact[]
}

export async function fetchIntel(
  client: SupabaseClient,
  leagueId: string,
  week: string,
): Promise<IntelSnapshot[]> {
  const { data, error } = await client
    .from('events')
    .select('vars')
    .eq('league_id', leagueId)
    .eq('week', week)
    .eq('kind', 'intel')
    .order('ts', { ascending: false })
  fail(error)
  return (data as { vars: IntelSnapshot }[]).map((row) => row.vars)
}

export async function fetchMySquad(
  client: SupabaseClient,
  leagueId: string,
  week: string,
  memberId: string,
): Promise<{ units: Record<string, number>; submittedAt: string | null; auto: boolean }> {
  const [units, squad] = await Promise.all([
    client
      .from('squad_units')
      .select('slot, instrument_id')
      .eq('league_id', leagueId)
      .eq('week', week)
      .eq('member_id', memberId),
    client
      .from('squads')
      .select('submitted_at, auto')
      .eq('league_id', leagueId)
      .eq('week', week)
      .eq('member_id', memberId)
      .maybeSingle(),
  ])
  fail(units.error)
  fail(squad.error)
  const result: Record<string, number> = {}
  for (const row of units.data as { slot: string; instrument_id: number }[]) {
    result[row.slot] = row.instrument_id
  }
  const metaRow: unknown = squad.data
  const meta = metaRow as { submitted_at: string | null; auto: boolean } | null
  return { units: result, submittedAt: meta?.submitted_at ?? null, auto: meta?.auto ?? false }
}
