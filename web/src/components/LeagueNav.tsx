import { NavLink } from 'react-router'
import { useI18n } from '../i18n/context'
import type { MessageKey } from '../i18n/en'

const TABS: { path: string; label: MessageKey }[] = [
  { path: 'lobby', label: 'nav.league.lobby' },
  { path: 'briefing', label: 'nav.league.briefing' },
  { path: 'front', label: 'nav.league.front' },
  { path: 'resupply', label: 'nav.league.resupply' },
  { path: 'debrief/latest', label: 'nav.league.debrief' },
  { path: 'campaign', label: 'nav.league.campaign' },
]

/** Tabs between the screens of one league. */
export function LeagueNav({ leagueId }: { leagueId: string }) {
  const { t } = useI18n()
  return (
    <nav className="league-nav" aria-label={t('nav.league')}>
      {TABS.map((tab) => (
        <NavLink key={tab.path} to={`/l/${leagueId}/${tab.path}`}>
          {t(tab.label)}
        </NavLink>
      ))}
    </nav>
  )
}
