import type { Unit } from '../data/week'
import { useI18n } from '../i18n/context'
import type { MessageKey } from '../i18n/en'
import { formatNumber, formatSignedPercent } from '../lib/format'

export function UnitFacts({ unit }: { unit: Unit }) {
  const { t, locale } = useI18n()
  const s = unit.stats
  return (
    <span className="unit-facts">
      <span className="tag">{unit.region}</span>
      <span>{t(`sector.${unit.sector}` as MessageKey)}</span>
      {s?.display_class && <span>{t(`class.${s.display_class}` as MessageKey)}</span>}
      {s?.coef != null && (
        <span title={t('unit.coef')}>
          {t('unit.coefShort', { coef: formatNumber(locale, s.coef, 2) })}
        </span>
      )}
      {s?.prev_week_return != null && (
        <span className={s.prev_week_return >= 0 ? 'up' : 'down'}>
          {t('unit.lastWeek', { pct: formatSignedPercent(locale, s.prev_week_return) })}
        </span>
      )}
      {s?.in_conflict_zone && <span className="badge badge-zone">{t('unit.zone')}</span>}
      {s?.weather.map((w) => (
        <span key={w} className={`badge weather-${w}`}>
          {t(`weather.${w}` as MessageKey)}
        </span>
      ))}
    </span>
  )
}

export function UnitCard({
  unit,
  slotLabel,
  disabled,
  onDeploy,
}: {
  unit: Unit
  slotLabel: string | null
  disabled: boolean
  onDeploy: () => void
}) {
  const { t } = useI18n()
  return (
    <li className="unit-card">
      <div className="unit-main">
        <span className="unit-title">
          <strong>{unit.ticker}</strong> <span className="muted">{unit.name}</span>
        </span>
        <UnitFacts unit={unit} />
      </div>
      {slotLabel && (
        <button
          type="button"
          className="button button-secondary"
          disabled={disabled}
          aria-label={t('briefing.deployAs', { ticker: unit.ticker, slot: slotLabel })}
          onClick={onDeploy}
        >
          {t('briefing.deploy')}
        </button>
      )}
    </li>
  )
}
