import { useState } from 'react'
import { CommanderEmblem } from '../components/CommanderEmblem'
import { commanderName } from '../components/commanderText'
import { Avatar } from '../components/MemberList'
import { slotKey } from '../briefing/squadRules'
import { useI18n } from '../i18n/context'
import { formatInstant, formatNumber, formatSignedPercent } from '../lib/format'
import { orderRows } from './orderRows'
import type { FrontData, LiveRow } from './useFront'

function Units({ data, row }: { data: FrontData; row: LiveRow }) {
  const { t, locale } = useI18n()
  const units = data.squads.filter((u) => u.member_id === row.member_id)
  if (units.length === 0) return <p className="muted">{t('front.squadHidden')}</p>
  return (
    <ul className="live-units">
      {units.map((u) => {
        const instrument = data.instruments.get(u.instrument_id)
        const move = data.returns.get(u.instrument_id)?.week_return_pct
        const pf = row.units[u.slot]
        return (
          <li key={u.slot}>
            <span>{t(slotKey(u.slot))}</span> <strong>{instrument?.ticker ?? '?'}</strong>
            {move != null && (
              <span className={move >= 0 ? 'up' : 'down'}> {formatSignedPercent(locale, move)}</span>
            )}
            <span className="live-pf">
              {row.jammed ? '???' : pf === undefined ? '—' : t('front.pf', { pf: formatNumber(locale, pf, 0) })}
            </span>
          </li>
        )
      })}
    </ul>
  )
}

export function Leaderboard({ data }: { data: FrontData }) {
  const { t, locale } = useI18n()
  const [open, setOpen] = useState<string | null>(null)
  const members = new Map(data.league.league_members.map((m) => [m.member_id, m]))
  const drone = data.league.league_members.find((m) => m.is_drone)?.member_id ?? null
  const shown = new Set(data.live.map((r) => r.member_id))
  const hidden = data.league.league_members.filter((m) => !m.is_drone && !shown.has(m.member_id))
  const rows = orderRows(data.live, drone)
  const updated = data.live.reduce<string | null>((max, r) => (max && max > r.updated_at ? max : r.updated_at), null)

  if (rows.length === 0) {
    return <p className="notice">{t('front.noScores')}</p>
  }
  return (
    <section aria-labelledby="board-h">
      <h2 id="board-h">{t('front.leaderboard')}</h2>
      {updated && <p className="muted">{t('front.updated', { time: formatInstant(locale, updated) })}</p>}
      <ol className="board">
        {rows.map((row) => {
          const m = members.get(row.member_id)
          const isOpen = open === row.member_id
          return (
            <li key={row.member_id} className={row.member_id === data.me.member_id ? 'board-row board-me' : 'board-row'}>
              <button
                type="button"
                className="board-line"
                aria-expanded={isOpen}
                onClick={() => {
                  setOpen(isOpen ? null : row.member_id)
                }}
              >
                <span className="board-rank">{row.rank_live ?? '—'}</span>
                <Avatar pseudo={m?.pseudo ?? '?'} color={m?.avatar_color ?? '#666666'} />
                <span className="board-name">
                  {m?.pseudo}
                  <span className="member-commander">
                    {m?.commander && <CommanderEmblem code={m.commander} size={16} />}
                    {commanderName(t, m?.commander ?? null)}
                  </span>
                </span>
                {row.member_id === drone && <span className="tag">{t('front.droneTag')}</span>}
                <span className="board-pf">
                  {row.jammed ? '???' : t('front.pf', { pf: formatNumber(locale, row.pf_live ?? 0, 0) })}
                </span>
              </button>
              {isOpen && <Units data={data} row={row} />}
            </li>
          )
        })}
      </ol>
      {hidden.length > 0 && (
        <p className="muted">{t('front.inShadows', { names: hidden.map((m) => m.pseudo).join(', ') })}</p>
      )}
    </section>
  )
}
