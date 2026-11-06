import { useMemo, useState, type ReactNode } from 'react'
import { I18nContext, useI18n, type I18nValue } from './context'
import type { MessageKey } from './en'
import { readGuideLocale, saveGuideLocale } from './guideLocale'
import { LOCALES, translate, type Locale, type Vars } from './translate'

export type T = (key: MessageKey, vars?: Vars) => string

/**
 * Renders `children` in the guide's language (useI18n() inside sees it). `children` receives
 * the app's own `t` (`ui`), for names the player sees on screen, and the EN/FR switch.
 */
export function GuideI18n({ children }: { children: (ui: T, languageSwitch: ReactNode) => ReactNode }) {
  const app = useI18n()
  const [locale, setLocale] = useState<Locale>(readGuideLocale)
  const value = useMemo<I18nValue>(
    () => ({ ...app, locale, t: (key: MessageKey, vars?: Vars) => translate(locale, key, vars) }),
    [app, locale],
  )
  const languageSwitch = (
    <div className="language-switch guide-language" role="group" aria-label={app.t('header.language')}>
      {LOCALES.map((code) => (
        <button
          key={code}
          type="button"
          lang={code}
          aria-pressed={locale === code}
          title={app.t(`language.${code}`)}
          onClick={() => {
            setLocale(code)
            saveGuideLocale(code)
          }}
        >
          {code.toUpperCase()}
        </button>
      ))}
    </div>
  )
  return <I18nContext value={value}>{children(app.t, languageSwitch)}</I18nContext>
}
