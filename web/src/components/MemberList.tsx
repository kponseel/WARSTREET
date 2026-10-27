import type { League } from '../data/leagues'
import { useI18n } from '../i18n/context'
import { BadgeChips } from './BadgeChips'
import { CommanderEmblem } from './CommanderEmblem'
import { commanderName } from './commanderText'
import { textOn } from '../lib/color'

export function Avatar({ pseudo, color }: { pseudo: string; color: string }) {
  return (
    <span className="avatar" style={{ background: color, color: textOn(color) }} aria-hidden="true">
      {pseudo.slice(0, 1).toUpperCase()}
    </span>
  )
}

export function MemberList({
  league,
  userId,
  badges,
}: {
  league: League
  userId: string
  badges?: ReadonlyMap<string, string[]>
}) {
  const { t } = useI18n()
  return (
    <ul className="member-list" aria-label={t('lobby.members')}>
      {league.league_members.map((m) => (
        <li key={m.member_id} className="member">
          <Avatar pseudo={m.pseudo} color={m.avatar_color} />
          <span className="member-main">
            <span className="member-name">
              {m.pseudo}
              {m.user_id === userId && <span className="tag">{t('lobby.you')}</span>}
              {m.user_id === league.host_id && <span className="tag">{t('lobby.host')}</span>}
              <BadgeChips codes={badges?.get(m.member_id) ?? []} />
            </span>
            <span className="member-commander">
              {m.commander && <CommanderEmblem code={m.commander} size={18} />}
              {commanderName(t, m.commander)}
            </span>
          </span>
          {!m.is_drone && (
            <span className={m.ready ? 'badge badge-ok' : 'badge'}>
              {t(m.ready ? 'lobby.ready' : 'lobby.notReady')}
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}
