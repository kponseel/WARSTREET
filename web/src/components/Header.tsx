import { Link } from 'react-router'
import { GAME_NAME } from '../config'
import { LanguageSwitch } from './LanguageSwitch'

export function Header() {
  return (
    <header className="app-header">
      <Link to="/" className="brand">
        <img src={`${import.meta.env.BASE_URL}icon.svg`} alt="" width={28} height={28} />
        <span>{GAME_NAME}</span>
      </Link>
      <LanguageSwitch />
    </header>
  )
}
