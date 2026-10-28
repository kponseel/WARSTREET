import { Link } from 'react-router'
import { GAME_NAME } from '../config'
import { useI18n } from '../i18n/context'
import { isDebug } from '../lib/log'
import { LanguageSwitch } from './LanguageSwitch'

export function Header() {
  const { t } = useI18n()
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
        <Link to="/tutorial">{t('nav.help')}</Link>
        <Link to="/rules">{t('nav.rules')}</Link>
        {isDebug() && <Link to="/debug">{t('nav.debug')}</Link>}
        <LanguageSwitch />
      </nav>
    </header>
  )
}
