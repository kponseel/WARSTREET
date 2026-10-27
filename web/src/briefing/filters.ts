import type { Unit } from '../data/week'

export const CLASSES = ['armored', 'infantry', 'commando', 'kamikaze']

export interface CatalogueFilters {
  search: string
  region: '' | 'EU' | 'US'
  sector: string
  displayClass: string
  zoneOnly: boolean
}

export const NO_FILTERS: CatalogueFilters = {
  search: '',
  region: '',
  sector: '',
  displayClass: '',
  zoneOnly: false,
}

export function filterUnits(units: readonly Unit[], f: CatalogueFilters): Unit[] {
  const query = f.search.trim().toLowerCase()
  return units.filter(
    (u) =>
      (query === '' || u.ticker.toLowerCase().includes(query) || u.name.toLowerCase().includes(query)) &&
      (f.region === '' || u.region === f.region) &&
      (f.sector === '' || u.sector === f.sector) &&
      (f.displayClass === '' || u.stats?.display_class === f.displayClass) &&
      (!f.zoneOnly || u.stats?.in_conflict_zone === true),
  )
}
