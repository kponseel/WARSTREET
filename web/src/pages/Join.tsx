import { useEffect, useState, type SyntheticEvent } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router'
import { useAuth } from '../auth/context'
import { ErrorMessage } from '../components/ErrorMessage'
import { MemberFields } from '../components/MemberFields'
import { emptyDraft, type MemberDraft } from '../components/memberDraft'
import { useGameConfig } from '../data/gameConfig'
import type { LeaguePreview } from '../data/leagues'
import { useI18n } from '../i18n/context'
import { callRpc, RpcFailure, toFailure } from '../lib/rpc'
import { useAction } from '../lib/useAction'

type PreviewState =
  | { status: 'loading' }
  | { status: 'error'; error: RpcFailure }
  | { status: 'ready'; preview: LeaguePreview }

export function Join() {
  const { code = '' } = useParams()
  const { client } = useAuth()
  const { t } = useI18n()
  const navigate = useNavigate()
  const config = useGameConfig(client)
  const [state, setState] = useState<PreviewState>({ status: 'loading' })
  const [draft, setDraft] = useState<MemberDraft | null>(null)
  const action = useAction()

  useEffect(() => {
    if (!client) return
    let active = true
    callRpc<LeaguePreview[]>(client, 'league_preview', { p_code: code }).then(
      (rows) => {
        const preview = rows[0]
        if (!active) return
        setState(
          preview
            ? { status: 'ready', preview }
            : { status: 'error', error: new RpcFailure('error.LEAGUE_NOT_FOUND') },
        )
      },
      (error: unknown) => {
        if (active) setState({ status: 'error', error: toFailure(error) })
      },
    )
    return () => {
      active = false
    }
  }, [client, code])

  if (state.status === 'loading' || !config) {
    return <p aria-busy="true">{t('common.loading')}</p>
  }
  if (state.status === 'error') {
    return (
      <section className="page narrow">
        <h1>{t('join.title')}</h1>
        <ErrorMessage error={state.error} />
        <Link to="/">{t('notFound.back')}</Link>
      </section>
    )
  }
  const { preview } = state
  if (preview.is_member) return <Navigate to={`/l/${preview.league_id}/lobby`} replace />

  const closed = preview.status !== 'lobby'
  const full = preview.players >= preview.max_players
  const current = draft ?? emptyDraft(config)

  const onSubmit = async (event: SyntheticEvent) => {
    event.preventDefault()
    if (!client) return
    await action.run(async () => {
      const id = await callRpc<string>(client, 'join_league', {
        p_code: code,
        p_pseudo: current.pseudo,
        p_commander: current.commander,
        p_avatar_color: current.color,
      })
      await navigate(`/l/${id}/lobby`, { replace: true })
    })
  }

  return (
    <section className="page narrow">
      <h1>{t('join.title')}</h1>
      <div className="card">
        <h2>{preview.name}</h2>
        <p className="muted">
          {preview.host_pseudo && t('join.host', { host: preview.host_pseudo })} ·{' '}
          {t('league.players', { n: preview.players, max: preview.max_players })}
        </p>
      </div>
      {closed || full ? (
        <p className="notice" role="status">
          {t(closed ? 'error.LEAGUE_NOT_IN_LOBBY' : 'error.LEAGUE_FULL', {
            max: preview.max_players,
          })}
        </p>
      ) : (
        <form className="form" onSubmit={(e) => void onSubmit(e)}>
          <MemberFields config={config} draft={current} onChange={setDraft} idPrefix="join" />
          <ErrorMessage error={action.error} />
          <button type="submit" className="button" disabled={action.pending}>
            {t('join.submit')}
          </button>
        </form>
      )}
    </section>
  )
}
