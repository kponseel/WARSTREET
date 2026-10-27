import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router'
import { useAuth } from '../auth/context'
import { OrdersPanel } from '../briefing/OrdersPanel'
import { frontErrors, frontSlots, reserveSlots, slotKey, type Squad } from '../briefing/squadRules'
import { Countdown } from '../components/Countdown'
import { ErrorMessage } from '../components/ErrorMessage'
import { LeagueNav } from '../components/LeagueNav'
import { useClock, useNow } from '../data/clockContext'
import { useGameConfig, type GameConfig } from '../data/gameConfig'
import { fetchLeague, type League, type Member } from '../data/leagues'
import {
  fetchAmmo,
  fetchMyOrders,
  fetchMySquad,
  fetchOrderCosts,
  type MyOrder,
  type OrderCost,
} from '../data/orders'
import { fetchUnits, fetchWeeks, type Unit, type Week } from '../data/week'
import { useI18n } from '../i18n/context'
import { localizeVars } from '../lib/localizeVars'
import { logEvent } from '../lib/log'
import { callRpc } from '../lib/rpc'
import { useAction } from '../lib/useAction'

interface Swap {
  slot: string
  reserve_slot: string
}

interface ResupplyData {
  league: League
  me: Member
  week: Week
  units: Unit[]
  squad: Record<string, number>
  swaps: Swap[]
  blockaded: boolean
  ammo: number
  costs: OrderCost[]
  orders: MyOrder[]
}

async function loadResupply(
  client: NonNullable<ReturnType<typeof useAuth>['client']>,
  leagueId: string,
  userId: string,
): Promise<ResupplyData | null> {
  const [league, weeks] = await Promise.all([fetchLeague(client, leagueId), fetchWeeks(client, leagueId)])
  const me = league?.league_members.find((m) => m.user_id === userId)
  const week = weeks.at(-1)
  if (!league || !me || !week) return null
  const [units, mine, swaps, blockade, ammo, costs, orders] = await Promise.all([
    fetchUnits(client, week.week),
    fetchMySquad(client, leagueId, week.week, me.member_id),
    client.from('swaps').select('slot, reserve_slot').eq('league_id', leagueId).eq('week', week.week).eq('member_id', me.member_id),
    client
      .from('orders_public')
      .select('id')
      .eq('league_id', leagueId)
      .eq('week', week.week)
      .eq('type', 'blockade')
      .eq('status', 'applied')
      .eq('target_member_id', me.member_id),
    fetchAmmo(client, leagueId, me.member_id),
    fetchOrderCosts(client, leagueId),
    fetchMyOrders(client, leagueId, week.week),
  ])
  if (swaps.error) throw new Error(swaps.error.message)
  if (blockade.error) throw new Error(blockade.error.message)
  const swapRows: unknown = swaps.data
  const blockadeRows: unknown = blockade.data
  return {
    league,
    me,
    week,
    units,
    squad: mine.units,
    swaps: swapRows as Swap[],
    blockaded: (blockadeRows as unknown[]).length > 0,
    ammo,
    costs,
    orders,
  }
}

function SwapPanel({
  data,
  config,
  onChange,
}: {
  data: ResupplyData
  config: GameConfig
  onChange: () => void
}) {
  const { t } = useI18n()
  const { client } = useAuth()
  const action = useAction()
  const [picking, setPicking] = useState<string | null>(null)
  const units = useMemo(() => new Map(data.units.map((u) => [u.id, u])), [data.units])
  const commander = data.me.commander
  const max = commander === 'quartermaster' ? config.num('quartermaster_max_swaps') : config.num('max_swaps')
  const reserves = reserveSlots(config, commander).filter((s) => data.squad[s] !== undefined)
  const usedReserves = new Set(data.swaps.map((s) => s.reserve_slot))
  const ticker = (slot: string) => {
    const id = data.squad[slot]
    return id === undefined ? '—' : (units.get(id)?.ticker ?? '?')
  }
  const frontAfter = (extra?: Swap): Squad => {
    const front: Squad = {}
    for (const slot of frontSlots(config)) front[slot] = data.squad[slot]
    for (const s of [...data.swaps.filter((w) => w.slot !== extra?.slot), ...(extra ? [extra] : [])]) {
      front[s.slot] = data.squad[s.reserve_slot]
    }
    return front
  }
  const call = (fn: string, args: Record<string, unknown>) =>
    action
      .run(async () => {
        if (client) await callRpc(client, fn, args)
      })
      .then((ok) => {
        if (ok) {
          setPicking(null)
          onChange()
        }
      })

  if (data.blockaded) {
    return <p className="notice">{t('error.BLOCKADED')}</p>
  }
  return (
    <section aria-labelledby="swap-h" className="card">
      <h2 id="swap-h">{t('resupply.swaps')}</h2>
      <p className="hint">{t('resupply.swapRule', { max, used: data.swaps.length })}</p>
      <ul className="slot-list">
        {frontSlots(config).map((slot) => {
          const swap = data.swaps.find((s) => s.slot === slot)
          return (
            <li key={slot} className="swap-row">
              <div>
                <strong>{t(slotKey(slot))}</strong> {ticker(slot)}
                {swap && (
                  <span className="swap-to">
                    {' '}
                    → {ticker(swap.reserve_slot)} <span className="tag">{t('resupply.pending')}</span>
                  </span>
                )}
              </div>
              {swap ? (
                <button
                  type="button"
                  className="button button-link"
                  disabled={action.pending}
                  onClick={() => void call('cancel_swap', { p_league: data.league.id, p_slot: slot })}
                >
                  {t('resupply.cancel')}
                </button>
              ) : picking === slot ? (
                <div className="row">
                  {reserves
                    .filter((r) => !usedReserves.has(r))
                    .map((r) => {
                      const problems = frontErrors(frontAfter({ slot, reserve_slot: r }), units, config)
                      return (
                        <button
                          key={r}
                          type="button"
                          className="button button-secondary"
                          disabled={action.pending || problems.length > 0}
                          title={problems.map((p) => t(p.key, localizeVars(t, p.vars))).join(' ')}
                          aria-label={t('resupply.swapWith', { unit: ticker(r) })}
                          onClick={() => void call('swap_unit', { p_league: data.league.id, p_slot: slot, p_reserve_slot: r })}
                        >
                          {ticker(r)}
                          {problems.length > 0 && ` · ${t('resupply.invalid')}`}
                        </button>
                      )
                    })}
                  <button
                    type="button"
                    className="button button-link"
                    onClick={() => {
                      setPicking(null)
                    }}
                  >
                    {t('common.cancel')}
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  className="button button-secondary"
                  disabled={action.pending || data.swaps.length >= max}
                  onClick={() => {
                    setPicking(slot)
                  }}
                >
                  {t('resupply.swap')}
                </button>
              )}
            </li>
          )
        })}
      </ul>
      <ErrorMessage error={action.error} />
    </section>
  )
}

export function Resupply() {
  const { id = '' } = useParams()
  const { client, session } = useAuth()
  const { t } = useI18n()
  const { synced } = useClock()
  const config = useGameConfig(client)
  const now = useNow(10_000).getTime()
  const [data, setData] = useState<ResupplyData | null | 'loading' | 'error'>('loading')
  const [version, setVersion] = useState(0)
  const userId = session?.user.id ?? ''

  useEffect(() => {
    if (!client) return
    const run = { cancelled: false }
    loadResupply(client, id, userId).then(
      (loaded) => {
        if (!run.cancelled) setData(loaded)
      },
      (error: unknown) => {
        logEvent('error', 'resupply', error instanceof Error ? error.message : String(error))
        if (!run.cancelled) setData('error')
      },
    )
    return () => {
      run.cancelled = true
    }
  }, [client, id, userId, version])

  if (data === 'loading' || !config || !synced) return <p aria-busy="true">{t('common.loading')}</p>
  if (data === 'error') {
    return (
      <p className="error" role="alert">
        {t('error.unknown')}
      </p>
    )
  }
  if (data === null) {
    return (
      <section className="page">
        <LeagueNav leagueId={id} />
        <p className="notice">{t('briefing.notStarted')}</p>
      </section>
    )
  }
  const { week } = data
  const opensAt = week.resupply_opens_at ? Date.parse(week.resupply_opens_at) : null
  const open = opensAt !== null && now >= opensAt && now < Date.parse(week.resupply_closes_at)
  const refresh = () => {
    setVersion((v) => v + 1)
  }

  return (
    <section className="page resupply">
      <LeagueNav leagueId={id} />
      <h1>{t('resupply.title', { n: week.number })}</h1>
      {open ? (
        <>
          <Countdown to={week.resupply_closes_at} label={t('resupply.closesIn')} />
          <SwapPanel data={data} config={config} onChange={refresh} />
          {!data.blockaded && (
            <OrdersPanel
              config={config}
              leagueId={id}
              members={data.league.league_members.filter((m) => !m.is_drone)}
              ammo={data.ammo}
              costs={data.costs}
              orders={data.orders.filter((o) => o.order_window === 'resupply')}
              intel={[]}
              onPlayed={refresh}
            />
          )}
        </>
      ) : opensAt !== null && now < opensAt ? (
        <Countdown to={new Date(opensAt).toISOString()} label={t('resupply.opensIn')} />
      ) : opensAt === null ? (
        <p className="notice">{t('resupply.notYet')}</p>
      ) : (
        <p className="notice">{t('resupply.closed')}</p>
      )}
    </section>
  )
}
