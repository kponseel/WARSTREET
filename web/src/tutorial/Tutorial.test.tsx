import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EXAMPLES } from '../content/examples.generated'
import { I18nProvider } from '../i18n/I18nProvider'
import { Tutorial } from './Tutorial'
import { isTutorialDismissed, wasTutorialSeenThisVisit } from './tutorialState'

function renderTutorial(auto: boolean, onDone = vi.fn()) {
  render(
    <I18nProvider locale="en">
      <MemoryRouter>
        <Tutorial auto={auto} onDone={onDone} />
      </MemoryRouter>
    </I18nProvider>,
  )
  return onDone
}

const next = () => {
  fireEvent.click(screen.getByRole('button', { name: 'Next' }))
}

describe('Tutorial', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.sessionStorage.clear()
  })

  it('walks through the 7 steps, with engine-computed numbers', () => {
    const onDone = renderTutorial(false)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Welcome to WARSTREET')
    expect(screen.getByText('Step 1 of 7', { exact: false })).toBeInTheDocument()
    next()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('War Points (₩)')
    const champion = EXAMPLES.week[0]
    expect(screen.getByText(`Champion ×2 · ${champion.name} +${champion.move.toFixed(1)} %: +${String(champion.pf)} ₩`)).toBeInTheDocument()
    expect(screen.getByText(`Units: +${String(EXAMPLES.weekUnitsTotal)} ₩`)).toBeInTheDocument()
    for (let i = 0; i < 4; i += 1) next()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Campaign points')
    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Credits and orders')
    next()
    next()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Commanders')
    expect(screen.getAllByText('See an example')).toHaveLength(7)
    expect(screen.queryByRole('button', { name: 'Next' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Start playing' }))
    expect(onDone).toHaveBeenCalledOnce()
    // Opened from Help: finishing never changes the "don't show again" choice.
    expect(isTutorialDismissed()).toBe(false)
  })

  it('at launch, skipping with the box ticked hides it for good', () => {
    const onDone = renderTutorial(true)
    expect(screen.getByRole('checkbox', { name: /Don’t show this automatically again/ })).toBeChecked()
    fireEvent.click(screen.getByRole('button', { name: 'Skip the tutorial' }))
    expect(onDone).toHaveBeenCalledOnce()
    expect(isTutorialDismissed()).toBe(true)
    expect(wasTutorialSeenThisVisit()).toBe(true)
  })

  it('at launch, unticking the box shows it again next launch only', () => {
    renderTutorial(true)
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: 'Skip the tutorial' }))
    expect(isTutorialDismissed()).toBe(false)
    expect(wasTutorialSeenThisVisit()).toBe(true)
  })
})
