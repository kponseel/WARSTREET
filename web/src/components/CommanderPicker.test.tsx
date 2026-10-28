import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import { EXAMPLES } from '../content/examples.generated'
import { GAME_CONFIG_VALUES } from '../content/gameConfig.generated'
import { GameConfig } from '../data/gameConfig'
import { I18nProvider } from '../i18n/I18nProvider'
import { CommanderPicker } from './CommanderPicker'

const CONFIG = GameConfig.fromValues(GAME_CONFIG_VALUES)

describe('CommanderPicker', () => {
  it('explains ₩ and shows an engine-computed example without picking the commander', () => {
    const onChange = vi.fn()
    render(
      <I18nProvider locale="en">
        <MemoryRouter>
          <CommanderPicker config={CONFIG} value={null} onChange={onChange} />
        </MemoryRouter>
      </I18nProvider>,
    )
    expect(screen.getByText(/₩ \(War Points\) is your weekly score/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'How to play' })).toHaveAttribute('href', '/tutorial')
    const examples = screen.getAllByText('See an example')
    expect(examples).toHaveLength(7)
    const first = examples[0]
    if (!first) throw new Error('no example')
    fireEvent.click(first)
    expect(onChange).not.toHaveBeenCalled()
    expect(
      screen.getByText(new RegExp(`${String(EXAMPLES.bastionBefore)} ₩ becomes ${String(EXAMPLES.bastionAfter)} ₩`)),
    ).toBeInTheDocument()
    // The radio keeps the commander's own text as its name.
    fireEvent.click(screen.getByRole('radio', { name: /The Bastion/ }))
    expect(onChange).toHaveBeenCalledWith('bastion')
  })
})
