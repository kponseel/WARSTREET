import { createContext, useContext } from 'react'
import type { MessageKey } from './en'
import type { Locale, Vars } from './translate'

export interface I18nValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  /** Counts language changes: a late profile read must not undo a newer choice. */
  localeVersion: () => number
  t: (key: MessageKey, vars?: Vars) => string
}

export const I18nContext = createContext<I18nValue | null>(null)

export function useI18n(): I18nValue {
  const value = useContext(I18nContext)
  if (!value) throw new Error('useI18n must be used inside <I18nProvider>')
  return value
}
