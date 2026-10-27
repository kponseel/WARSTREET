import { useAuth } from '../auth/context'
import { ErrorMessage } from '../components/ErrorMessage'
import type { Member } from '../data/leagues'
import type { Pact } from '../data/orders'
import { useI18n } from '../i18n/context'
import { callRpc } from '../lib/rpc'
import { useAction } from '../lib/useAction'

export function PactsPanel({
  leagueId,
  me,
  members,
  pacts,
  open,
  onChange,
}: {
  leagueId: string
  me: Member
  members: Member[]
  pacts: Pact[]
  open: boolean
  onChange: () => void
}) {
  const { t } = useI18n()
  const { client } = useAuth()
  const action = useAction()
  const pseudo = (id: string) => members.find((m) => m.member_id === id)?.pseudo ?? '—'
  const active = pacts.filter((p) => p.status === 'active')
  const mine = active.find((p) => [p.proposer_member_id, p.partner_member_id].includes(me.member_id))
  const received = pacts.filter((p) => p.status === 'proposed' && p.partner_member_id === me.member_id)
  const sent = pacts.filter((p) => p.status === 'proposed' && p.proposer_member_id === me.member_id)
  const others = members.filter((m) => !m.is_drone && m.member_id !== me.member_id)

  const call = (fn: string, args: Record<string, unknown>) =>
    action
      .run(async () => {
        if (client) await callRpc(client, fn, args)
      })
      .then((ok) => {
        if (ok) onChange()
      })

  return (
    <section aria-labelledby="pacts-h" className="card pacts">
      <h2 id="pacts-h">{t('pacts.title')}</h2>
      <p className="hint">{t('pacts.intro')}</p>
      {active.length > 0 && (
        <ul className="pact-list">
          {active.map((p) => (
            <li key={p.id}>
              {t('pacts.active', { a: pseudo(p.proposer_member_id), b: pseudo(p.partner_member_id) })}
            </li>
          ))}
        </ul>
      )}
      {received.map((p) => (
        <div key={p.id} className="row pact-received">
          <span>{t('pacts.received', { from: pseudo(p.proposer_member_id) })}</span>
          {open && (
            <>
              <button
                type="button"
                className="button"
                disabled={action.pending}
                onClick={() => void call('accept_pact', { p_pact: p.id })}
              >
                {t('pacts.accept')}
              </button>
              <button
                type="button"
                className="button button-secondary"
                disabled={action.pending}
                onClick={() => void call('decline_pact', { p_pact: p.id })}
              >
                {t('pacts.decline')}
              </button>
            </>
          )}
        </div>
      ))}
      {sent.map((p) => (
        <p key={p.id} className="muted">
          {t('pacts.sent', { to: pseudo(p.partner_member_id) })}
        </p>
      ))}
      {open && !mine && (
        <ul className="pact-propose">
          {others
            .filter((m) => !sent.some((p) => p.partner_member_id === m.member_id))
            .map((m) => (
              <li key={m.member_id} className="row">
                <span>{m.pseudo}</span>
                <button
                  type="button"
                  className="button button-secondary"
                  disabled={action.pending}
                  aria-label={t('pacts.proposeTo', { name: m.pseudo })}
                  onClick={() => void call('propose_pact', { p_league: leagueId, p_partner: m.member_id })}
                >
                  {t('pacts.propose')}
                </button>
              </li>
            ))}
        </ul>
      )}
      <ErrorMessage error={action.error} />
    </section>
  )
}
