import { Link } from 'react-router'
import { useAuth } from '../auth/context'
import { GAME_NAME } from '../config'
import { useI18n } from '../i18n/context'
import { LanguageSwitch } from './LanguageSwitch'

export function Header() {
  const { t } = useI18n()
  const { session, signOut } = useAuth()
  return (
    <header className="app-header">
      <a className="skip-link" href="#main" onClick={(e) => {
        e.preventDefault()
        document.getElementById('main')?.focus()
      }}>
        {t('nav.skip')}
      </a>
      <Link to="/" className="brand">
        <img src={`${import.meta.env.BASE_URL}icon.svg`} alt="" width={28} height={28} />
        <span>{GAME_NAME}</span>
      </Link>
      <nav className="header-nav" aria-label={t('nav.main')}>
        <Link to="/rules">{t('nav.rules')}</Link>
        {session && (
          <button type="button" className="header-button" onClick={() => void signOut()}>
            {t('nav.logout')}
          </button>
        )}
        <LanguageSwitch />
      </nav>
    </header>
  )
}
