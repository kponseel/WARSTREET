import { useState, type SyntheticEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAuth } from '../auth/context'
import { ErrorMessage } from '../components/ErrorMessage'
import { LandingIcon } from '../components/LandingIcon'
import { MemberFields } from '../components/MemberFields'
import { emptyDraft, type MemberDraft } from '../components/memberDraft'
import { GAME_NAME } from '../config'
import { useGameConfig, type GameConfig } from '../data/gameConfig'
import { humans, useMyLeagues, type League } from '../data/leagues'
import { useI18n } from '../i18n/context'
import { callRpc } from '../lib/rpc'
import { useAction } from '../lib/useAction'

function range(min: number, max: number): number[] {
  return Array.from({ length: max - min + 1 }, (_, i) => min + i)
}

function Landing() {
  const { t } = useI18n()
  const steps = [
    { kind: 'draft', title: 'landing.step1.title', text: 'landing.step1.text' },
    { kind: 'attack', title: 'landing.step2.title', text: 'landing.step2.text' },
    { kind: 'win', title: 'landing.step3.title', text: 'landing.step3.text' },
  ] as const
  return (
    <section className="page landing">
      <img className="landing-logo" src={`${import.meta.env.BASE_URL}icon.svg`} alt="" width={88} height={88} />
      <h1>{t('home.title', { game: GAME_NAME })}</h1>
      <p className="lead">{t('app.tagline')}</p>
      <ol className="landing-steps">
        {steps.map((step) => (
          <li key={step.kind} className="card landing-step">
            <LandingIcon kind={step.kind} />
            <span>
              <strong>{t(step.title)}</strong>
              <span>{t(step.text)}</span>
            </span>
          </li>
        ))}
      </ol>
      <div className="landing-actions">
        <Link className="button" to="/login">
          {t('home.login')}
        </Link>
        <Link className="button button-secondary" to="/tutorial">
          {t('tutorial.label')}
        </Link>
        <Link to="/rules">{t('nav.rules')}</Link>
      </div>
    </section>
  )
}
function LeagueCard({ league }: { league: League }) {
  const { t } = useI18n()
  return (
    <li className="card league-card">
      <div>
        <h3>{league.name}</h3>
        <p className="muted">
          {t(`league.status.${league.status}`)} ·{' '}
          {t('league.players', { n: humans(league).length, max: league.max_players })}
        </p>
      </div>
      <Link className="button button-secondary" to={`/l/${league.id}/lobby`}>
        {t('home.open')}
        <span className="visually-hidden"> {league.name}</span>
      </Link>
    </li>
  )
}

function CreateLeague({ config }: { config: GameConfig }) {
  const { t } = useI18n()
  const { client } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [maxPlayers, setMaxPlayers] = useState(config.num('max_players'))
  const [weeks, setWeeks] = useState(config.num('campaign_weeks_default'))
  const [drone, setDrone] = useState(true)
  const [draft, setDraft] = useState<MemberDraft>(() => emptyDraft(config))
  const action = useAction()

  const onSubmit = async (event: SyntheticEvent) => {
    event.preventDefault()
    if (!client) return
    await action.run(async () => {
      const id = await callRpc<string>(client, 'create_league', {
        p_name: name,
        p_max_players: maxPlayers,
        p_campaign_weeks: weeks,
        p_drone_enabled: drone,
        p_pseudo: draft.pseudo,
        p_commander: draft.commander,
        p_avatar_color: draft.color,
      })
      await navigate(`/l/${id}/lobby`)
    })
  }

  return (
    <form className="form card" onSubmit={(e) => void onSubmit(e)} aria-labelledby="create-title">
      <h2 id="create-title">{t('home.create')}</h2>
      <div className="field">
        <label htmlFor="league-name">{t('league.name')}</label>
        <input
          id="league-name"
          required
          maxLength={config.num('league_name_max_length')}
          value={name}
          onChange={(e) => {
            setName(e.target.value)
          }}
        />
      </div>
      <div className="field-row">
        <div className="field">
          <label htmlFor="league-max">{t('league.maxPlayers')}</label>
          <select
            id="league-max"
            value={maxPlayers}
            onChange={(e) => {
              setMaxPlayers(Number(e.target.value))
            }}
          >
            {range(config.num('min_players'), config.num('max_players')).map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="league-weeks">{t('league.weeks')}</label>
          <select
            id="league-weeks"
            value={weeks}
            onChange={(e) => {
              setWeeks(Number(e.target.value))
            }}
          >
            {range(config.num('campaign_weeks_min'), config.num('campaign_weeks_max')).map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="field checkbox">
        <input
          id="league-drone"
          type="checkbox"
          checked={drone}
          onChange={(e) => {
            setDrone(e.target.checked)
          }}
        />
        <label htmlFor="league-drone">{t('league.drone')}</label>
      </div>
      <MemberFields config={config} draft={draft} onChange={setDraft} idPrefix="create" />
      <ErrorMessage error={action.error} />
      <button type="submit" className="button" disabled={action.pending}>
        {t('home.createSubmit')}
      </button>
    </form>
  )
}

function JoinByCode({ config }: { config: GameConfig }) {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [code, setCode] = useState('')
  const length = config.num('invite_code_length')
  return (
    <form
      className="form card"
      aria-labelledby="join-title"
      onSubmit={(e) => {
        e.preventDefault()
        void navigate(`/join/${code.trim().toUpperCase()}`)
      }}
    >
      <h2 id="join-title">{t('home.join')}</h2>
      <div className="field">
        <label htmlFor="join-code">{t('home.joinCode')}</label>
        <input
          id="join-code"
          required
          minLength={length}
          maxLength={length}
          autoCapitalize="characters"
          autoComplete="off"
          spellCheck={false}
          value={code}
          onChange={(e) => {
            setCode(e.target.value.toUpperCase())
          }}
        />
      </div>
      <button type="submit" className="button button-secondary">
        {t('home.joinSubmit')}
      </button>
    </form>
  )
}

function Dashboard() {
  const { t } = useI18n()
  const { client, signOut } = useAuth()
  const config = useGameConfig(client)
  const leagues = useMyLeagues(client)
  return (
    <section className="page">
      <h1>{t('home.myLeagues')}</h1>
      {leagues.status === 'loading' && <p aria-busy="true">{t('common.loading')}</p>}
      {leagues.status === 'error' && (
        <p className="error" role="alert">
          {t('error.unknown')}
        </p>
      )}
      {leagues.status === 'ready' &&
        (leagues.data.length === 0 ? (
          <p className="muted">{t('home.noLeague')}</p>
        ) : (
          <ul className="league-list">
            {leagues.data.map((league) => (
              <LeagueCard key={league.id} league={league} />
            ))}
          </ul>
        ))}
      {config ? (
        <div className="stack">
          <JoinByCode config={config} />
          <CreateLeague config={config} />
        </div>
      ) : (
        <p aria-busy="true">{t('common.loading')}</p>
      )}
      <p className="muted page-footer">
        <Link to="/status">{t('status.link')}</Link>
        {' · '}
        <button type="button" className="button-link" onClick={() => void signOut()}>
          {t('nav.logout')}
        </button>
      </p>
    </section>
  )
}

export function Home() {
  const { client, session, loading } = useAuth()
  const { t } = useI18n()
  if (!client) {
    return (
      <>
        <Landing />
        <p className="status status-missing">{t('home.backend.missing')}</p>
      </>
    )
  }
  if (loading) return <p aria-busy="true">{t('common.loading')}</p>
  return session ? <Dashboard /> : <Landing />
}
