import { useAuth } from '../auth/context'
import { useI18n } from '../i18n/context'
import { LOCALES } from '../i18n/translate'

export function LanguageSwitch() {
  const { locale, setLocale, t } = useI18n()
  const { client, session } = useAuth()
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
            // Logged in: the choice is saved in profiles.locale (every device, server messages).
            // (A Supabase query only runs once awaited or then-ed.)
            if (client && session) {
              void client.rpc('set_locale', { p_locale: code }).then(() => undefined)
            }
          }}
        >
          {code.toUpperCase()}
        </button>
      ))}
    </div>
  )
}
