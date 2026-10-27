import type { GameConfig } from '../data/gameConfig'
import type { Unit } from '../data/week'
import { useI18n } from '../i18n/context'
import { formatNumber } from '../lib/format'
import { frontSlots, reserveSlots, slotKey, type Squad } from './squadRules'

export function SlotBoard({
  config,
  commander,
  squad,
  units,
  active,
  editable,
  onSelect,
  onClear,
}: {
  config: GameConfig
  commander: string | null
  squad: Squad
  units: ReadonlyMap<number, Unit>
  active: string | null
  editable: boolean
  onSelect: (slot: string) => void
  onClear: (slot: string) => void
}) {
  const { t, locale } = useI18n()
  const row = (slot: string, multiplier: number | null) => {
    const id = squad[slot]
    const unit = id === undefined ? undefined : units.get(id)
    const label = t(slotKey(slot))
    return (
      <li key={slot} className={active === slot ? 'slot slot-active' : 'slot'}>
        <button
          type="button"
          className="slot-pick"
          aria-pressed={active === slot}
          disabled={!editable}
          onClick={() => {
            onSelect(slot)
          }}
        >
          <span className="slot-name">
            {label}
            {multiplier !== null && <span className="muted"> ×{formatNumber(locale, multiplier)}</span>}
          </span>
          <span className={unit ? 'slot-unit' : 'slot-unit muted'}>
            {unit ? `${unit.ticker} · ${unit.region}` : t('briefing.empty')}
          </span>
        </button>
        {unit && editable && (
          <button
            type="button"
            className="button button-link"
            aria-label={t('briefing.remove', { slot: label })}
            onClick={() => {
              onClear(slot)
            }}
          >
            ✕
          </button>
        )}
      </li>
    )
  }
  return (
    <div className="slot-board">
      <h3>{t('briefing.front')}</h3>
      <ul className="slot-list">
        {frontSlots(config).map((slot) => row(slot, config.numIn('slot_multipliers', slot)))}
      </ul>
      <h3>{t('briefing.reserve')}</h3>
      <ul className="slot-list">{reserveSlots(config, commander).map((slot) => row(slot, null))}</ul>
    </div>
  )
}
