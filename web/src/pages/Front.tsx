import { Link, useParams } from 'react-router'
import { useAuth } from '../auth/context'
import { Countdown } from '../components/Countdown'
import { LeagueNav } from '../components/LeagueNav'
import { useClock, useNow } from '../data/clockContext'
import { EventFeed } from '../front/EventFeed'
import { Leaderboard } from '../front/Leaderboard'
import { MyUnits } from '../front/MyUnits'
import { PhaseBanner } from '../front/PhaseBanner'
import { useFront } from '../front/useFront'
import { useI18n } from '../i18n/context'

export function Front() {
  const { id = '' } = useParams()
  const { client, session } = useAuth()
  const { t } = useI18n()
  const { synced } = useClock()
  const state = useFront(client, id, session?.user.id ?? '')
  const now = useNow(10_000).getTime()

  if (state.status === 'loading' || !synced) return <p aria-busy="true">{t('common.loading')}</p>
  if (state.status === 'error') {
    return (
      <p className="error" role="alert">
        {t('error.unknown')}
      </p>
    )
  }
  if (state.status === 'not-started') {
    return (
      <section className="page">
        <LeagueNav leagueId={id} />
        <p className="notice">{t('briefing.notStarted')}</p>
      </section>
    )
  }
  const { data } = state
  const { week } = data
  const locked = now >= Date.parse(week.lock_at)
  const resupplyOpen =
    week.resupply_opens_at !== null &&
    now >= Date.parse(week.resupply_opens_at) &&
    now < Date.parse(week.resupply_closes_at)
  const debriefed = week.phase === 'debrief'

  return (
    <section className="page front">
      <LeagueNav leagueId={id} />
      <h1>{t('front.title', { n: week.number })}</h1>
      {week.is_final && <p className="final-banner">{t('briefing.final')}</p>}
      <PhaseBanner sessions={data.sessions} />
      {!locked && (
        <div className="notice">
          <p>{t('front.beforeLock')}</p>
          <Link className="button" to={`/l/${id}/briefing`}>
            {t('lobby.toBriefing')}
          </Link>
        </div>
      )}
      {resupplyOpen && (
        <div className="notice">
          <Countdown to={week.resupply_closes_at} label={t('front.resupplyCloses')} />
          <Link className="button" to={`/l/${id}/resupply`}>
            {t('front.toResupply')}
          </Link>
        </div>
      )}
      {debriefed && <p className="notice">{t('front.debriefed')}</p>}
      {locked && <MyUnits data={data} />}
      {locked && <Leaderboard data={data} />}
      <EventFeed data={data} />
    </section>
  )
}
