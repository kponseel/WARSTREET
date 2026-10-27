import { useI18n } from '../i18n/context'
import { LOCALES } from '../i18n/translate'

export function LanguageSwitch() {
  const { locale, setLocale, t } = useI18n()
  return (
    <div className="language-switch" role="group" aria-label={t('header.language')}>
      {LOCALES.map((code) => (
        <button
          key={code}
          type="button"
          lang={code}
          aria-pressed={locale === code}
          title={t(`language.${code}`)}
          onClick={() => {
            setLocale(code)
          }}
        >
          {code.toUpperCase()}
        </button>
      ))}
    </div>
  )
}
