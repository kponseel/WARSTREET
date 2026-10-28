import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { GAME_NAME } from '../config'
import { I18nProvider } from '../i18n/I18nProvider'
import { App } from './App'

function renderApp(locale?: 'en' | 'fr') {
  return render(
    <I18nProvider {...(locale ? { locale } : {})}>
      <App />
    </I18nProvider>,
  )
}

describe('App', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.location.hash = ''
  })

  it('renders the home page in English', () => {
    renderApp('en')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(`Welcome to ${GAME_NAME}`)
    expect(document.documentElement.lang).toBe('en')
  })

  it('renders the home page in French', () => {
    renderApp('fr')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(`Bienvenue sur ${GAME_NAME}`)
    expect(document.documentElement.lang).toBe('fr')
  })

  it('shows the build version and time at the bottom of the page', () => {
    renderApp('fr')
    expect(screen.getByRole('contentinfo')).toHaveTextContent(
      new RegExp(`^Version ${__BUILD_SHA__} · mise à jour : .+`),
    )
  })

  it('has no language switch and stays in English while French is off', () => {
    window.localStorage.setItem('locale', 'fr')
    renderApp()
    expect(screen.queryByRole('button', { name: 'FR' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(`Welcome to ${GAME_NAME}`)
  })

  it('shows the not-found page for unknown routes', () => {
    window.location.hash = '#/nowhere'
    renderApp('en')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Page not found')
  })

  it('shows that the server is not configured when the build has no Supabase variables', () => {
    renderApp('en')
    expect(screen.getByText('Server connection not configured yet.')).toBeInTheDocument()
  })
})
