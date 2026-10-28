import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { TutorialGate } from './TutorialGate'
import { dismissTutorial } from './tutorialState'

const auth = vi.hoisted(() => ({ session: null as object | null }))
vi.mock('../auth/context', () => ({ useAuth: () => auth }))

function renderGate(path = '/') {
  render(
    <I18nProvider locale="en">
      <MemoryRouter initialEntries={[path]}>
        <TutorialGate>
          <p>The page</p>
        </TutorialGate>
      </MemoryRouter>
    </I18nProvider>,
  )
}

describe('TutorialGate', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.sessionStorage.clear()
    auth.session = { user: { id: 'u1' } }
  })

  it('shows the tutorial first to a logged-in newcomer, then the page', () => {
    renderGate('/join/ABC234')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Welcome to WARSTREET')
    expect(screen.queryByText('The page')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Skip the tutorial' }))
    expect(screen.getByText('The page')).toBeInTheDocument()
  })

  it('stays out of the way when dismissed, logged out, or on the rules page', () => {
    auth.session = null
    renderGate()
    expect(screen.getByText('The page')).toBeInTheDocument()
  })

  it('is not shown again once dismissed', () => {
    dismissTutorial()
    renderGate()
    expect(screen.getByText('The page')).toBeInTheDocument()
  })

  it('never blocks the rules page', () => {
    renderGate('/rules')
    expect(screen.getByText('The page')).toBeInTheDocument()
  })
})
