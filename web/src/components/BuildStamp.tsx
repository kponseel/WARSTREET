import { useI18n } from '../i18n/context'
import { formatInstant } from '../lib/format'

/** "Version bd4de04 · updated Wed 28 Oct, 18:14 CET": which build this page runs. */
export function BuildStamp() {
  const { locale, t } = useI18n()
  return (
    <footer className="app-footer">
      <small>{t('app.build', { sha: __BUILD_SHA__, date: formatInstant(locale, __BUILD_TIME__) })}</small>
    </footer>
  )
}
