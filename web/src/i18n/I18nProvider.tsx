import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { MessageKey } from './en'
import { I18nContext, type I18nValue } from './context'
import { detectLocale, isLocale, translate, type Locale, type Vars } from './translate'

// Per-browser convenience until profiles.locale is wired (milestone 05, set_locale RPC).
const STORAGE_KEY = 'locale'

function readStoredLocale(): Locale | null {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    return isLocale(stored) ? stored : null
  } catch {
    return null
  }
}

function initialLocale(): Locale {
  return readStoredLocale() ?? detectLocale(navigator.languages)
}

export function I18nProvider({
  children,
  locale: forcedLocale,
}: {
  children: ReactNode
  locale?: Locale
}) {
  const [locale, setLocaleState] = useState<Locale>(() => forcedLocale ?? initialLocale())

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next)
    try {
      window.localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Storage can be unavailable (private mode); the choice then lasts for this visit.
    }
  }, [])

  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])

  const value = useMemo<I18nValue>(
    () => ({
      locale,
      setLocale,
      t: (key: MessageKey, vars?: Vars) => translate(locale, key, vars),
    }),
    [locale, setLocale],
  )

  return <I18nContext value={value}>{children}</I18nContext>
}
