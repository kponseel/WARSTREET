import { useMemo, useState } from 'react'
import type { Unit } from '../data/week'
import { useI18n } from '../i18n/context'
import type { MessageKey } from '../i18n/en'
import { CLASSES, filterUnits, type CatalogueFilters } from './filters'
import { UnitCard } from './UnitCard'

export function Catalogue({
  units,
  used,
  slotLabel,
  filters,
  onFilters,
  onDeploy,
}: {
  units: readonly Unit[]
  used: ReadonlySet<number>
  slotLabel: string | null
  filters: CatalogueFilters
  onFilters: (filters: CatalogueFilters) => void
  onDeploy: (unit: Unit) => void
}) {
  const { t } = useI18n()
  const [limit, setLimit] = useState(30)
  const sectors = useMemo(() => [...new Set(units.map((u) => u.sector))].sort(), [units])
  const shown = filterUnits(units, filters)
  return (
    <section aria-labelledby="catalogue-h" className="catalogue">
      <h2 id="catalogue-h">{t('briefing.catalogue')}</h2>
      <div className="filters">
        <div className="field">
          <label htmlFor="f-search">{t('briefing.search')}</label>
          <input
            id="f-search"
            type="search"
            value={filters.search}
            onChange={(e) => {
              onFilters({ ...filters, search: e.target.value })
            }}
          />
        </div>
        <div className="field">
          <label htmlFor="f-region">{t('briefing.region')}</label>
          <select
            id="f-region"
            value={filters.region}
            onChange={(e) => {
              onFilters({ ...filters, region: e.target.value as CatalogueFilters['region'] })
            }}
          >
            <option value="">{t('briefing.all')}</option>
            <option value="EU">{t('region.EU')}</option>
            <option value="US">{t('region.US')}</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="f-sector">{t('briefing.sector')}</label>
          <select
            id="f-sector"
            value={filters.sector}
            onChange={(e) => {
              onFilters({ ...filters, sector: e.target.value })
            }}
          >
            <option value="">{t('briefing.all')}</option>
            {sectors.map((s) => (
              <option key={s} value={s}>
                {t(`sector.${s}` as MessageKey)}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="f-class">{t('briefing.class')}</label>
          <select
            id="f-class"
            value={filters.displayClass}
            onChange={(e) => {
              onFilters({ ...filters, displayClass: e.target.value })
            }}
          >
            <option value="">{t('briefing.all')}</option>
            {CLASSES.map((c) => (
              <option key={c} value={c}>
                {t(`class.${c}` as MessageKey)}
              </option>
            ))}
          </select>
        </div>
        <div className="field checkbox">
          <input
            id="f-zone"
            type="checkbox"
            checked={filters.zoneOnly}
            onChange={(e) => {
              onFilters({ ...filters, zoneOnly: e.target.checked })
            }}
          />
          <label htmlFor="f-zone">{t('briefing.zoneOnly')}</label>
        </div>
      </div>
      <p className="muted" role="status">
        {t('briefing.count', { n: shown.length })}
      </p>
      <ul className="unit-list">
        {shown.slice(0, limit).map((unit) => (
          <UnitCard
            key={unit.id}
            unit={unit}
            slotLabel={slotLabel}
            disabled={used.has(unit.id)}
            onDeploy={() => {
              onDeploy(unit)
            }}
          />
        ))}
      </ul>
      {shown.length > limit && (
        <button
          type="button"
          className="button button-secondary"
          onClick={() => {
            setLimit(limit + 30)
          }}
        >
          {t('briefing.more')}
        </button>
      )}
    </section>
  )
}
