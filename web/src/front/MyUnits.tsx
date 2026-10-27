import { slotKey } from '../briefing/squadRules'
import { useI18n } from '../i18n/context'
import { formatNumber, formatSignedPercent } from '../lib/format'
import type { FrontData } from './useFront'

/** My units with their live PF (??? while I am jammed; prices and returns stay visible). */
export function MyUnits({ data }: { data: FrontData }) {
  const { t, locale } = useI18n()
  const mine = data.squads.filter((u) => u.member_id === data.me.member_id)
  const jammed = data.myLive === null && data.live.some((r) => r.member_id === data.me.member_id && r.jammed)
  if (mine.length === 0) return <p className="notice">{t('front.noSquad')}</p>
  return (
    <section aria-labelledby="mine-h" className="card">
      <h2 id="mine-h">{t('front.mySquad')}</h2>
      <p className="my-total">
        {jammed ? t('front.jammed') : t('front.myPf', { pf: formatNumber(locale, data.myLive?.pf_live ?? 0, 0) })}
      </p>
      <ul className="live-units">
        {mine.map((u) => {
          const instrument = data.instruments.get(u.instrument_id)
          const r = data.returns.get(u.instrument_id)
          const pf = data.myLive?.units[u.slot]
          const segment = u.active_s1 && !u.active_s2 ? t('front.s1Only') : !u.active_s1 && u.active_s2 ? t('front.s2Only') : null
          return (
            <li key={u.slot}>
              <span>{t(slotKey(u.slot))}</span> <strong>{instrument?.ticker ?? '?'}</strong>
              {segment && <span className="tag">{segment}</span>}
              {r?.week_return_pct != null && (
                <span className={r.week_return_pct >= 0 ? 'up' : 'down'}> {formatSignedPercent(locale, r.week_return_pct)}</span>
              )}
              <span className="live-pf">
                {jammed ? '???' : pf === undefined ? '—' : t('front.pf', { pf: formatNumber(locale, pf, 0) })}
              </span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
