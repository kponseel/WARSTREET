import { useRef, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useAuth } from '../auth/context'
import { BadgeChips } from '../components/BadgeChips'
import { LeagueNav } from '../components/LeagueNav'
import { Avatar } from '../components/MemberList'
import { GAME_NAME } from '../config'
import { BreakdownTable } from '../debrief/BreakdownTable'
import { useCampaign } from '../debrief/data'
import { drawShareCard, shareOrDownload } from '../debrief/shareCard'
import { useI18n } from '../i18n/context'
import type { MessageKey } from '../i18n/en'
import { formatDay, formatNumber } from '../lib/format'

export function Debrief() {
  const { id = '', week: weekParam = '' } = useParams()
  const { client, session } = useAuth()
  const { t, locale } = useI18n()
  const state = useCampaign(client, id)
  const [open, setOpen] = useState<string | null>(null)
  const [shared, setShared] = useState<string | null>(null)
  const canvas = useRef<HTMLCanvasElement>(null)

  if (state.status === 'loading') return <p aria-busy="true">{t('common.loading')}</p>
  if (state.status === 'error' || !state.data) {
    return (
      <p className="error" role="alert">
        {t('error.unknown')}
      </p>
    )
  }
  const data = state.data
  const debriefed = [...new Set(data.scores.map((s) => s.week))].sort()
  const week = weekParam === 'latest' || weekParam === '' ? debriefed.at(-1) : weekParam
  const weekRow = data.weeks.find((w) => w.week === week)
  const scores = data.scores.filter((s) => s.week === week)
  if (!week || !weekRow || scores.length === 0) {
    return (
      <section className="page">
        <LeagueNav leagueId={id} />
        <h1>{t('debrief.title')}</h1>
        <p className="notice">{t('debrief.none')}</p>
      </section>
    )
  }
  const members = new Map(data.league.league_members.map((m) => [m.member_id, m]))
  const drone = scores.find((s) => members.get(s.member_id)?.is_drone)
  const humans = scores.filter((s) => !members.get(s.member_id)?.is_drone).sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99))
  const badges = data.badges.filter((b) => b.week === week)
  const badgesOf = (member: string) => badges.filter((b) => b.member_id === member).map((b) => b.code)
  const dispatch = data.dispatches.find((d) => d.week === week)
  const me = data.league.league_members.find((m) => m.user_id === session?.user.id)
  const index = debriefed.indexOf(week)
  const pf = (value: number) => t('front.pf', { pf: formatNumber(locale, value, 0) })
  const points = (value: number) => t('debrief.points', { n: formatNumber(locale, value) })

  const share = async () => {
    if (!canvas.current) return
    drawShareCard(canvas.current, {
      game: GAME_NAME,
      title: t('debrief.cardTitle', { n: weekRow.number }),
      subtitle: data.league.name,
      entries: humans.slice(0, 3).map((s) => ({
        rank: s.rank ?? 0,
        pseudo: members.get(s.member_id)?.pseudo ?? '?',
        color: members.get(s.member_id)?.avatar_color ?? '#ffffff',
        pf: pf(s.pf_total),
        points: points(s.campaign_points),
      })),
    })
    const result = await shareOrDownload(canvas.current, `podium-week-${String(weekRow.number)}.png`)
    setShared(result)
  }

  return (
    <section className="page debrief">
      <LeagueNav leagueId={id} />
      <h1>{t('debrief.weekTitle', { n: weekRow.number })}</h1>
      <p className="muted">{formatDay(locale, week)}</p>
      {weekRow.is_final && <p className="final-banner">{t('debrief.finalDouble')}</p>}
      <nav className="row" aria-label={t('debrief.weeks')}>
        {index > 0 && <Link to={`/l/${id}/debrief/${debriefed[index - 1] ?? ''}`}>{t('debrief.previous')}</Link>}
        {index < debriefed.length - 1 && (
          <Link to={`/l/${id}/debrief/${debriefed[index + 1] ?? ''}`}>{t('debrief.next')}</Link>
        )}
      </nav>

      {dispatch && (
        <blockquote className="dispatch">
          <p className="dispatch-label">{t('term.dispatch')}</p>
          <p>{t(`${dispatch.template_key}.${String(dispatch.variant)}` as MessageKey, dispatch.vars)}</p>
        </blockquote>
      )}

      <h2>{t('debrief.ranking')}</h2>
      <ol className="board">
        {humans.map((s) => {
          const m = members.get(s.member_id)
          const isOpen = open === s.member_id
          return (
            <li key={s.member_id} className={m?.member_id === me?.member_id ? 'board-row board-me' : 'board-row'}>
              <button
                type="button"
                className="board-line"
                aria-expanded={isOpen}
                onClick={() => {
                  setOpen(isOpen ? null : s.member_id)
                }}
              >
                <span className="board-rank">{s.rank ?? '—'}</span>
                <Avatar pseudo={m?.pseudo ?? '?'} color={m?.avatar_color ?? '#666666'} />
                <span className="board-name">
                  {m?.pseudo}
                  <BadgeChips codes={badgesOf(s.member_id)} />
                </span>
                <span className="board-pf">
                  {pf(s.pf_total)}
                  <span className="points">+{points(s.campaign_points)}</span>
                </span>
              </button>
              {isOpen && <BreakdownTable breakdown={s.breakdown} instruments={data.instruments} />}
            </li>
          )
        })}
      </ol>

      {drone && (
        <section aria-labelledby="drone-h" className="card">
          <h2 id="drone-h">{t('debrief.droneVerdict')}</h2>
          <p>{t('debrief.droneScore', { pf: pf(drone.pf_total) })}</p>
          <ul className="drone-list">
            {humans.map((s) => {
              const rusty = badgesOf(s.member_id).includes('rusty')
              return (
                <li key={s.member_id} className={rusty ? 'down' : 'up'}>
                  {members.get(s.member_id)?.pseudo}: {t('debrief.picking')} {pf(s.pf_picking)} —{' '}
                  {t(rusty ? 'debrief.beatenByDrone' : 'debrief.beatDrone')}
                </li>
              )
            })}
          </ul>
        </section>
      )}

      <section aria-labelledby="share-h" className="card">
        <h2 id="share-h">{t('debrief.share')}</h2>
        <button type="button" className="button" onClick={() => void share()}>
          {t('debrief.shareButton')}
        </button>
        {shared && <p role="status">{t(shared === 'shared' ? 'debrief.sharedDone' : 'debrief.downloaded')}</p>}
        <canvas ref={canvas} className="share-canvas" aria-hidden="true" />
      </section>
    </section>
  )
}
