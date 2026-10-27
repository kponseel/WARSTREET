import { Link, useParams } from 'react-router'
import { useAuth } from '../auth/context'
import { BadgeChips } from '../components/BadgeChips'
import { LeagueNav } from '../components/LeagueNav'
import { Avatar } from '../components/MemberList'
import { sortStandings, useCampaign, type CampaignData } from '../debrief/data'
import { useI18n } from '../i18n/context'
import { formatNumber } from '../lib/format'

const CHART_W = 640
const CHART_H = 260
const PAD = 36

/** Cumulative campaign points per week, one line per player (numbers from scores_final). */
function PointsChart({ data }: { data: CampaignData }) {
  const { t, locale } = useI18n()
  const weeks = [...new Set(data.scores.map((s) => s.week))].sort()
  const humans = data.league.league_members.filter((m) => !m.is_drone)
  if (weeks.length === 0) return null
  const series = humans.map((m) => {
    let total = 0
    return {
      member: m,
      points: weeks.map((w) => {
        total += data.scores.find((s) => s.week === w && s.member_id === m.member_id)?.campaign_points ?? 0
        return total
      }),
    }
  })
  const max = Math.max(1, ...series.flatMap((s) => s.points))
  const x = (i: number) => PAD + (weeks.length === 1 ? (CHART_W - 2 * PAD) / 2 : (i * (CHART_W - 2 * PAD)) / (weeks.length - 1))
  const y = (v: number) => CHART_H - PAD - (v / max) * (CHART_H - 2 * PAD)
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${String(CHART_W)} ${String(CHART_H)}`} role="img" aria-labelledby="chart-title">
        <title id="chart-title">{t('campaign.chartTitle')}</title>
        <line x1={PAD} y1={CHART_H - PAD} x2={CHART_W - PAD} y2={CHART_H - PAD} className="axis" />
        {weeks.map((w, i) => (
          <text key={w} x={x(i)} y={CHART_H - PAD + 22} textAnchor="middle" className="tick">
            {t('campaign.weekShort', { n: i + 1 })}
          </text>
        ))}
        {series.map((s) => (
          <g key={s.member.member_id}>
            <polyline
              fill="none"
              stroke={s.member.avatar_color}
              strokeWidth="3"
              points={s.points.map((v, i) => `${String(x(i))},${String(y(v))}`).join(' ')}
            />
            {s.points.map((v, i) => (
              <circle key={weeks[i]} cx={x(i)} cy={y(v)} r="4" fill={s.member.avatar_color} />
            ))}
          </g>
        ))}
      </svg>
      <figcaption className="legend">
        {series.map((s) => (
          <span key={s.member.member_id}>
            <span className="legend-dot" style={{ background: s.member.avatar_color }} aria-hidden="true" />
            {s.member.pseudo} ({formatNumber(locale, s.points.at(-1) ?? 0)})
          </span>
        ))}
      </figcaption>
    </figure>
  )
}

export function Campaign() {
  const { id = '' } = useParams()
  const { client } = useAuth()
  const { t, locale } = useI18n()
  const state = useCampaign(client, id)

  if (state.status === 'loading') return <p aria-busy="true">{t('common.loading')}</p>
  if (state.status === 'error' || !state.data) {
    return (
      <p className="error" role="alert">
        {t('error.unknown')}
      </p>
    )
  }
  const data = state.data
  const members = new Map(data.league.league_members.map((m) => [m.member_id, m]))
  const standings = sortStandings(data.standings)
  const current = data.weeks.at(-1)
  const finished = data.league.status === 'finished'
  const collection = new Map<string, Map<string, number>>()
  for (const b of data.badges) {
    const mine = collection.get(b.member_id) ?? new Map<string, number>()
    mine.set(b.code, (mine.get(b.code) ?? 0) + 1)
    collection.set(b.member_id, mine)
  }

  return (
    <section className="page campaign">
      <LeagueNav leagueId={id} />
      <h1>{t('campaign.title')}</h1>
      <p className="muted">
        {data.league.name} · {t('campaign.progress', { n: current?.number ?? 0, total: data.league.campaign_weeks })}
      </p>
      {current?.is_final && !finished && <p className="final-banner">{t('briefing.final')}</p>}

      {finished && standings.length > 0 && (
        <section aria-labelledby="podium-h" className="podium-section">
          <h2 id="podium-h">{t('campaign.podium')}</h2>
          <ol className="podium">
            {standings.slice(0, 3).map((s, i) => {
              const m = members.get(s.member_id)
              return (
                <li key={s.member_id} className={`podium-${String(i + 1)}`}>
                  <Avatar pseudo={m?.pseudo ?? '?'} color={m?.avatar_color ?? '#666666'} />
                  <strong>{m?.pseudo}</strong>
                  <span>{t('debrief.points', { n: formatNumber(locale, s.campaign_points) })}</span>
                </li>
              )
            })}
          </ol>
        </section>
      )}

      <h2>{t('campaign.standings')}</h2>
      <table className="standings">
        <thead>
          <tr>
            <th scope="col">#</th>
            <th scope="col">{t('campaign.player')}</th>
            <th scope="col" className="num">{t('term.campaign_points')}</th>
            <th scope="col" className="num">{t('campaign.wins')}</th>
            <th scope="col" className="num">{t('campaign.pfTotal')}</th>
          </tr>
        </thead>
        <tbody>
          {standings.map((s, i) => (
            <tr key={s.member_id}>
              <td>{i + 1}</td>
              <th scope="row">{members.get(s.member_id)?.pseudo}</th>
              <td className="num">{formatNumber(locale, s.campaign_points)}</td>
              <td className="num">{s.weekly_wins}</td>
              <td className="num">{formatNumber(locale, s.pf_cumulative, 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="hint">{t('campaign.tiebreak')}</p>

      <h2>{t('campaign.chart')}</h2>
      {data.scores.length === 0 ? <p className="muted">{t('debrief.none')}</p> : <PointsChart data={data} />}

      <h2>{t('campaign.badges')}</h2>
      {collection.size === 0 ? (
        <p className="muted">{t('campaign.noBadge')}</p>
      ) : (
        <ul className="badge-collection">
          {[...collection.entries()].map(([member, codes]) => (
            <li key={member}>
              <strong>{members.get(member)?.pseudo}</strong>{' '}
              {[...codes.entries()].map(([code, n]) => (
                <span key={code} className="badge-count">
                  <BadgeChips codes={[code]} /> ×{n}
                </span>
              ))}
            </li>
          ))}
        </ul>
      )}

      <h2>{t('campaign.weeks')}</h2>
      <ul className="week-links">
        {[...new Set(data.scores.map((s) => s.week))].sort().map((w, i) => (
          <li key={w}>
            <Link to={`/l/${id}/debrief/${w}`}>{t('debrief.weekTitle', { n: i + 1 })}</Link>
          </li>
        ))}
      </ul>
    </section>
  )
}
