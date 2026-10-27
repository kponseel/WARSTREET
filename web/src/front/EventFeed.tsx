import { slotKey } from '../briefing/squadRules'
import { useI18n } from '../i18n/context'
import type { MessageKey } from '../i18n/en'
import { formatInstant } from '../lib/format'
import type { FrontData } from './useFront'

interface Item {
  id: string
  ts: string
  text: string
  kind: string
}

/** Front Dispatch editions, resolved orders and my intel, newest first. */
export function EventFeed({ data }: { data: FrontData }) {
  const { t, locale } = useI18n()
  const pseudo = (id: string | null) => data.league.league_members.find((m) => m.member_id === id)?.pseudo ?? '?'
  const items: Item[] = [
    ...data.events.map((e) => ({
      id: `e${String(e.id)}`,
      ts: e.ts,
      kind: e.kind,
      text:
        e.kind === 'dispatch'
          ? t(`${e.template_key}.${String(e.variant)}` as MessageKey, e.vars)
          : t('feed.intel', { target: pseudo(String(e.vars.target_member_id)) }),
    })),
    ...data.orders.map((o) => ({
      id: `o${o.id}`,
      ts: o.resolved_at,
      kind: o.status === 'blocked' ? 'blocked' : 'order',
      text: t(o.status === 'blocked' ? 'feed.blocked' : o.type === 'force_field' ? 'feed.shield' : 'feed.order', {
        attacker: o.member_id ? pseudo(o.member_id) : t('feed.anonymous'),
        order: t(`order.${o.type}` as MessageKey),
        target: o.target_member_id ? pseudo(o.target_member_id) : pseudo(o.member_id),
        slot: o.target_slot ? t(slotKey(o.target_slot)) : '',
      }),
    })),
  ].sort((a, b) => b.ts.localeCompare(a.ts))

  return (
    <section aria-labelledby="feed-h">
      <h2 id="feed-h">{t('feed.title')}</h2>
      {items.length === 0 ? (
        <p className="muted">{t('feed.empty')}</p>
      ) : (
        <ol className="feed">
          {items.map((item) => (
            <li key={item.id} className={`feed-${item.kind}`}>
              <time dateTime={item.ts} className="muted">
                {formatInstant(locale, item.ts)}
              </time>
              <p>{item.text}</p>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
