import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { Rules } from './Rules'

function renderRules() {
  render(
    <I18nProvider locale="en">
      <MemoryRouter>
        <Rules />
      </MemoryRouter>
    </I18nProvider>,
  )
}

describe('Rules', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('switches to French like Help, keeping the names shown in the app', () => {
    renderRules()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Rules')
    fireEvent.click(screen.getByRole('button', { name: 'FR' }))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Règles')
    expect(screen.getByRole('heading', { name: /The Bastion/ })).toBeInTheDocument()
    expect(window.localStorage.getItem('guide.locale')).toBe('fr')
  })

  it('opens in the language last picked in Help or Rules', () => {
    window.localStorage.setItem('guide.locale', 'fr')
    renderRules()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Règles')
  })
})
