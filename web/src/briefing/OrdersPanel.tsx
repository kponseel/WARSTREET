import { useState } from 'react'
import { useAuth } from '../auth/context'
import { ErrorMessage } from '../components/ErrorMessage'
import type { GameConfig } from '../data/gameConfig'
import type { Member } from '../data/leagues'
import type { IntelSnapshot, MyOrder, OrderCost } from '../data/orders'
import { useI18n } from '../i18n/context'
import type { MessageKey } from '../i18n/en'
import { formatInstant } from '../lib/format'
import { callRpc } from '../lib/rpc'
import { useAction } from '../lib/useAction'
import { slotKey } from './squadRules'

interface Draft {
  type: string
  target: string
  slot: string
}

function orderKind(config: GameConfig, type: string): string {
  const orders = config.raw('orders') as Record<string, { kind: string }>
  return orders[type]?.kind ?? ''
}

export function OrdersPanel({
  config,
  leagueId,
  members,
  ammo,
  costs,
  orders,
  intel,
  onPlayed,
}: {
  config: GameConfig
  leagueId: string
  members: Member[]
  ammo: number
  costs: OrderCost[]
  orders: MyOrder[]
  intel: IntelSnapshot[]
  onPlayed: () => void
}) {
  const { t, locale } = useI18n()
  const { client } = useAuth()
  const action = useAction()
  const [draft, setDraft] = useState<Draft | null>(null)
  const [confirming, setConfirming] = useState(false)
  const pseudo = (id: string | null) => members.find((m) => m.member_id === id)?.pseudo ?? '—'
  const types = [...new Set(costs.map((c) => c.type))]
  const targeted = new Set(config.strings('targeted_orders'))
  const withSlot = new Set(config.strings('orders_with_target_slot'))
  const window = costs[0]?.order_window ?? null

  const costOf = (d: Draft): number | null => {
    const match = costs.find(
      (c) => c.type === d.type && (c.target_member_id ?? '') === (targeted.has(d.type) ? d.target : ''),
    )
    return match?.cost ?? null
  }

  const slotChoices = (type: string): string[] =>
    config.strings('front_slots').filter((s) => !(type === 'field_promotion' && s === 'champion'))

  const play = async () => {
    if (!client || !draft) return
    const ok = await action.run(async () => {
      await callRpc(client, 'play_order', {
        p_league: leagueId,
        p_type: draft.type,
        p_target_member: targeted.has(draft.type) ? draft.target : null,
        p_target_slot: withSlot.has(draft.type) ? draft.slot : null,
      })
    })
    setConfirming(false)
    if (ok) {
      setDraft(null)
      onPlayed()
    }
  }

  return (
    <section aria-labelledby="orders-h" className="card orders">
      <h2 id="orders-h">{t('orders.title')}</h2>
      <p>
        {t('orders.ammo')} <strong className="ammo">{ammo}</strong>
      </p>
      {window === null ? (
        <p className="muted">{t('error.ORDER_WINDOW_CLOSED')}</p>
      ) : (
        <ul className="order-list">
          {types.map((type) => {
            const prices = costs.filter((c) => c.type === type).map((c) => c.cost)
            const min = Math.min(...prices)
            const max = Math.max(...prices)
            const open = draft?.type === type
            return (
              <li key={type} className={open ? 'order order-open' : 'order'}>
                <div className="order-head">
                  <strong>{t(`order.${type}` as MessageKey)}</strong>
                  <span className={`badge kind-${orderKind(config, type)}`}>
                    {t(`orders.kind.${orderKind(config, type)}` as MessageKey)}
                  </span>
                  <span className="order-cost">
                    {min === max ? t('orders.cost', { n: min }) : t('orders.costRange', { min, max })}
                  </span>
                </div>
                <p className="order-desc">{t(`order.${type}.desc` as MessageKey)}</p>
                {type === 'force_field' && <p className="hint">{t('orders.hidden')}</p>}
                {!open ? (
                  <button
                    type="button"
                    className="button button-secondary"
                    onClick={() => {
                      action.clear()
                      setConfirming(false)
                      setDraft({
                        type,
                        target: costs.find((c) => c.type === type)?.target_member_id ?? '',
                        slot: slotChoices(type)[0] ?? '',
                      })
                    }}
                  >
                    {t('orders.prepare')}
                  </button>
                ) : (
                  <div className="form">
                    {targeted.has(type) && (
                      <div className="field">
                        <label htmlFor={`target-${type}`}>{t('orders.target')}</label>
                        <select
                          id={`target-${type}`}
                          value={draft.target}
                          onChange={(e) => {
                            setDraft({ ...draft, target: e.target.value })
                            setConfirming(false)
                          }}
                        >
                          {costs
                            .filter((c) => c.type === type && c.target_member_id)
                            .map((c) => (
                              <option key={c.target_member_id} value={c.target_member_id ?? ''}>
                                {pseudo(c.target_member_id)}
                                {c.target_has_bounty ? ` · ${t('orders.bounty')}` : ''}
                              </option>
                            ))}
                        </select>
                      </div>
                    )}
                    {withSlot.has(type) && (
                      <div className="field">
                        <label htmlFor={`slot-${type}`}>{t('orders.slot')}</label>
                        <select
                          id={`slot-${type}`}
                          value={draft.slot}
                          onChange={(e) => {
                            setDraft({ ...draft, slot: e.target.value })
                            setConfirming(false)
                          }}
                        >
                          {slotChoices(type).map((s) => (
                            <option key={s} value={s}>
                              {t(slotKey(s))}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                    {confirming ? (
                      <div className="confirm" role="group" aria-label={t('orders.confirmTitle')}>
                        <p>
                          {t('orders.confirm', {
                            order: t(`order.${type}` as MessageKey),
                            cost: costOf(draft) ?? '?',
                          })}
                        </p>
                        <div className="row">
                          <button
                            type="button"
                            className="button"
                            disabled={action.pending}
                            onClick={() => void play()}
                          >
                            {t('orders.play')}
                          </button>
                          <button
                            type="button"
                            className="button button-link"
                            onClick={() => {
                              setConfirming(false)
                            }}
                          >
                            {t('common.cancel')}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="row">
                        <button
                          type="button"
                          className="button"
                          onClick={() => {
                            setConfirming(true)
                          }}
                        >
                          {t('orders.review', { cost: costOf(draft) ?? '?' })}
                        </button>
                        <button
                          type="button"
                          className="button button-link"
                          onClick={() => {
                            setDraft(null)
                          }}
                        >
                          {t('common.cancel')}
                        </button>
                      </div>
                    )}
                    <ErrorMessage error={action.error} />
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}

      {orders.length > 0 && (
        <>
          <h3>{t('orders.mine')}</h3>
          <ul className="played-list">
            {orders.map((o) => (
              <li key={o.id}>
                {t(`order.${o.type}` as MessageKey)}
                {o.target_member_id ? ` → ${pseudo(o.target_member_id)}` : ''}
                {o.target_slot ? ` (${t(slotKey(o.target_slot))})` : ''} ·{' '}
                {t('orders.cost', { n: o.cost })} ·{' '}
                <span className={`status-${o.status}`}>{t(`orders.status.${o.status}` as MessageKey)}</span>
              </li>
            ))}
          </ul>
        </>
      )}

      {intel.map((snap) => (
        <div key={snap.taken_at} className="intel card">
          <h3>{t('orders.intelTitle', { target: pseudo(snap.target_member_id) })}</h3>
          <p className="hint">
            {t('orders.intelTaken', { time: formatInstant(locale, snap.taken_at) })}
          </p>
          {Object.keys(snap.units).length === 0 ? (
            <p>{t('orders.intelEmpty')}</p>
          ) : (
            <ul>
              {Object.entries(snap.units).map(([slot, ticker]) => (
                <li key={slot}>
                  {t(slotKey(slot))}: <strong>{ticker}</strong>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </section>
  )
}
