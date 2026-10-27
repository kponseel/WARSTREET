import { slotKey } from '../briefing/squadRules'
import type { Instrument } from '../data/week'
import { useI18n } from '../i18n/context'
import type { MessageKey } from '../i18n/en'
import { formatNumber, formatSignedPercent } from '../lib/format'
import { bestAndWorst, lines, type Breakdown, type SegmentDetail } from './breakdown'

function Segment({
  label,
  s,
  ticker,
}: {
  label: string
  s: SegmentDetail | null
  ticker: (id: number | null) => string
}) {
  const { t, locale } = useI18n()
  if (!s) return null
  return (
    <span className="segment">
      {label}: {ticker(s.instrument_id)}{' '}
      {s.missing || s.return === null ? t('debrief.missingPrice') : formatSignedPercent(locale, s.return)} ×
      {formatNumber(locale, s.multiplier)} ×{formatNumber(locale, s.coef, 2)}
      {s.modifier !== 1 && ` ×${formatNumber(locale, s.modifier, 2)}`} = {formatNumber(locale, s.pf)}
    </span>
  )
}

/** One player's week, line by line, exactly as the engine computed it. */
export function BreakdownTable({
  breakdown,
  instruments,
}: {
  breakdown: Breakdown
  instruments: ReadonlyMap<number, Instrument>
}) {
  const { t, locale } = useI18n()
  const ticker = (id: number | null) => (id === null ? '—' : (instruments.get(id)?.ticker ?? String(id)))
  const pf = (value: number) => t('front.pf', { pf: formatNumber(locale, value, 0) })
  const extremes = bestAndWorst(breakdown)
  return (
    <>
      <table className="breakdown">
        <caption className="visually-hidden">{t('debrief.breakdown')}</caption>
        <tbody>
          {Object.entries(breakdown.slots).map(([slot, d]) => (
            <tr key={slot}>
              <th scope="row">
                {t(slotKey(slot))}
                {d.swapped_from && <span className="tag">{t('debrief.swapped')}</span>}
              </th>
              <td>
                <Segment label={t('debrief.s1')} s={d.s1} ticker={ticker} />
                <Segment label={t('debrief.s2')} s={d.s2} ticker={ticker} />
                {d.orders.length > 0 && (
                  <span className="segment muted">{d.orders.map((o) => t(`order.${o}` as MessageKey)).join(', ')}</span>
                )}
                {d.clamped && <span className="segment muted">{t('debrief.clamped')}</span>}
              </td>
              <td className="num">{pf(d.pf)}</td>
            </tr>
          ))}
          <tr className="subtotal">
            <th scope="row">{t('debrief.picking')}</th>
            <td />
            <td className="num">{pf(breakdown.pf_picking)}</td>
          </tr>
          {lines(breakdown).map((line, index) => (
            <tr key={`${line.key}-${String(index)}`}>
              <th scope="row">
                {line.key === 'feat' && line.code
                  ? t(`feat.${line.code}` as MessageKey)
                  : t(`debrief.line.${line.key}` as MessageKey)}
              </th>
              <td />
              <td className="num">{pf(line.pf)}</td>
            </tr>
          ))}
          <tr className="total">
            <th scope="row">{t('debrief.total')}</th>
            <td />
            <td className="num">{pf(breakdown.pf_total)}</td>
          </tr>
        </tbody>
      </table>
      {extremes && (
        <p className="extremes">
          {t('debrief.bestUnit', {
            slot: t(slotKey(extremes.best.slot)),
            ticker: ticker(extremes.best.instrument_id),
            pf: pf(extremes.best.pf),
          })}{' '}
          ·{' '}
          {t('debrief.worstUnit', {
            slot: t(slotKey(extremes.worst.slot)),
            ticker: ticker(extremes.worst.instrument_id),
            pf: pf(extremes.worst.pf),
          })}
        </p>
      )}
    </>
  )
}
