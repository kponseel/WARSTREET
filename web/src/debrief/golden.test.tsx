import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Instrument } from '../data/week'
import { I18nProvider } from '../i18n/I18nProvider'
import { translate } from '../i18n/translate'
import type { Breakdown } from './breakdown'
import { lines } from './breakdown'
import { BreakdownTable } from './BreakdownTable'

// The golden weeks of milestone 02 (engine/tests/golden): the expected breakdown of every
// player, as the engine computes it. The debrief must show exactly those numbers.
interface Golden {
  players: Record<string, { breakdown: Breakdown; is_drone?: boolean }>
}
const files = import.meta.glob<Golden>('../../../engine/tests/golden/*.json', {
  eager: true,
  import: 'default',
})

const instruments = new Map<number, Instrument>()
const pf = (value: number) => translate('en', 'front.pf', { pf: new Intl.NumberFormat('en', { maximumFractionDigits: 0 }).format(value) })

describe('golden weeks render their exact breakdown', () => {
  const entries = Object.entries(files)
  it('finds the golden files', () => {
    expect(entries.length).toBeGreaterThanOrEqual(3)
  })

  for (const [file, golden] of entries) {
    for (const [player, result] of Object.entries(golden.players)) {
      it(`${file.split('/').at(-1) ?? file} · ${player}`, () => {
        const b = result.breakdown
        render(
          <I18nProvider locale="en">
            <BreakdownTable breakdown={b} instruments={instruments} />
          </I18nProvider>,
        )
        const table = screen.getByRole('table')
        const rows = within(table).getAllByRole('row')
        // One row per slot, the picking subtotal, one per extra line, the total.
        expect(rows).toHaveLength(Object.keys(b.slots).length + 1 + lines(b).length + 1)
        Object.values(b.slots).forEach((slot, i) => {
          expect(rows[i]).toHaveTextContent(pf(slot.pf))
        })
        const picking = Object.keys(b.slots).length
        expect(rows[picking]).toHaveTextContent(pf(b.pf_picking))
        lines(b).forEach((line, i) => {
          expect(rows[picking + 1 + i]).toHaveTextContent(pf(line.pf))
        })
        expect(rows.at(-1)).toHaveTextContent(pf(b.pf_total))
        // The lines add up to the total the engine stored (nothing recomputed, only checked).
        const sum = b.pf_picking + lines(b).reduce((s, l) => s + l.pf, 0)
        expect(sum).toBe(b.pf_total)
      })
    }
  }
})
