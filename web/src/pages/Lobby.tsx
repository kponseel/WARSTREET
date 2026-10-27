import { useState, type SyntheticEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useAuth } from '../auth/context'
import { CopyButton } from '../components/CopyButton'
import { ErrorMessage } from '../components/ErrorMessage'
import { MemberFields } from '../components/MemberFields'
import type { MemberDraft } from '../components/memberDraft'
import { MemberList } from '../components/MemberList'
import { useGameConfig, type GameConfig } from '../data/gameConfig'
import {
  canStart,
  humans,
  inviteLink,
  readyCount,
  useLeagueRoom,
  type League,
  type Member,
} from '../data/leagues'
import { useI18n } from '../i18n/context'
import { formatDay } from '../lib/format'
import { callRpc } from '../lib/rpc'
import { useAction } from '../lib/useAction'

function MySettings({ league, me, config }: { league: League; me: Member; config: GameConfig }) {
  const { t } = useI18n()
  const { client } = useAuth()
  const [draft, setDraft] = useState<MemberDraft | null>(null)
  const [saved, setSaved] = useState(false)
  const action = useAction()
  const current = draft ?? { pseudo: me.pseudo, commander: me.commander, color: me.avatar_color }

  const onSubmit = async (event: SyntheticEvent) => {
    event.preventDefault()
    if (!client) return
    setSaved(false)
    const ok = await action.run(async () => {
      await callRpc(client, 'update_member', {
        p_league: league.id,
        p_pseudo: current.pseudo,
        p_commander: current.commander,
        p_avatar_color: current.color,
      })
    })
    if (ok) {
      setDraft(null)
      setSaved(true)
    }
  }

  return (
    <details className="card">
      <summary>{t('lobby.mySettings')}</summary>
      <form className="form" onSubmit={(e) => void onSubmit(e)}>
        <MemberFields
          config={config}
          draft={current}
          onChange={(next) => {
            setDraft(next)
            setSaved(false)
          }}
          idPrefix="me"
        />
        <ErrorMessage error={action.error} />
        {saved && <p role="status">{t('common.saved')}</p>}
        <button type="submit" className="button" disabled={action.pending}>
          {t('common.save')}
        </button>
      </form>
    </details>
  )
}

function LobbyActions({ league, me, config }: { league: League; me: Member; config: GameConfig }) {
  const { t } = useI18n()
  const { client, session } = useAuth()
  const navigate = useNavigate()
  const action = useAction()
  const [confirmLeave, setConfirmLeave] = useState(false)
  const min = config.num('min_players')
  const userId = session?.user.id ?? ''
  const isHost = league.host_id === userId
  const ready = readyCount(league)

  const rpc = (fn: string, args: Record<string, unknown>) =>
    action.run(async () => {
      if (client) await callRpc(client, fn, args)
    })

  return (
    <div className="stack">
      <button
        type="button"
        className={me.ready ? 'button button-ok' : 'button'}
        aria-pressed={me.ready}
        disabled={action.pending}
        onClick={() => void rpc('set_ready', { p_league: league.id, p_ready: !me.ready })}
      >
        {t(me.ready ? 'lobby.imReady' : 'lobby.markReady')}
      </button>
      {isHost && (
        <div className="card">
          <p id="start-hint">{t('lobby.readyCount', { ready, min })}</p>
          <button
            type="button"
            className="button"
            aria-describedby="start-hint"
            disabled={action.pending || !canStart(league, userId, min)}
            onClick={() => void rpc('start_campaign', { p_league: league.id })}
          >
            {t('lobby.start')}
          </button>
        </div>
      )}
      <ErrorMessage error={action.error} />
      {confirmLeave ? (
        <div className="row" role="group" aria-label={t('lobby.leave')}>
          <span>{t('lobby.leaveConfirm')}</span>
          <button
            type="button"
            className="button button-danger"
            disabled={action.pending}
            onClick={() => {
              void action
                .run(async () => {
                  if (client) await callRpc(client, 'leave_league', { p_league: league.id })
                })
                .then((ok) => {
                  if (ok) void navigate('/', { replace: true })
                })
            }}
          >
            {t('lobby.leaveYes')}
          </button>
          <button
            type="button"
            className="button button-link"
            onClick={() => {
              setConfirmLeave(false)
            }}
          >
            {t('common.cancel')}
          </button>
        </div>
      ) : (
        <button
          type="button"
          className="button button-link"
          onClick={() => {
            setConfirmLeave(true)
          }}
        >
          {t('lobby.leave')}
        </button>
      )}
    </div>
  )
}

export function Lobby() {
  const { id = '' } = useParams()
  const { client, session } = useAuth()
  const { t, locale } = useI18n()
  const config = useGameConfig(client)
  const room = useLeagueRoom(client, id)
  const userId = session?.user.id ?? ''

  if (room.status === 'loading' || !config) return <p aria-busy="true">{t('common.loading')}</p>
  if (room.status === 'error' || !room.data) {
    return (
      <section className="page narrow">
        <h1>{t('lobby.notFound')}</h1>
        <Link to="/">{t('notFound.back')}</Link>
      </section>
    )
  }
  const league = room.data
  const me = league.league_members.find((m) => m.user_id === userId)
  const link = inviteLink(window.location, league.invite_code)

  return (
    <section className="page">
      <h1>{league.name}</h1>
      <p className="muted">
        {t(`league.status.${league.status}`)} ·{' '}
        {t('league.players', { n: humans(league).length, max: league.max_players })} ·{' '}
        {t('league.weeksCount', { n: league.campaign_weeks })}
      </p>

      {league.status === 'lobby' ? (
        <div className="card invite">
          <h2>{t('lobby.invite')}</h2>
          <p>
            {t('lobby.code')} <strong className="code">{league.invite_code}</strong>
          </p>
          <CopyButton text={link} label={t('lobby.copyLink')} />
        </div>
      ) : (
        <p className="notice" role="status">
          {league.start_week
            ? t('lobby.started', { day: formatDay(locale, league.start_week) })
            : t(`league.status.${league.status}`)}
        </p>
      )}

      <h2>{t('lobby.members')}</h2>
      <MemberList league={league} userId={userId} />

      {league.status === 'lobby' && me && (
        <>
          <LobbyActions league={league} me={me} config={config} />
          <MySettings league={league} me={me} config={config} />
        </>
      )}
    </section>
  )
}
