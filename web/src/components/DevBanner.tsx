import { useClock, useNow } from '../data/clockContext'
import { useI18n } from '../i18n/context'
import { DISPLAY_TIME_ZONE } from '../lib/format'

/** Shown when the database runs on a simulated clock (local dev mode only). */
export function DevBanner() {
  const { devClock } = useClock()
  const now = useNow(1000)
  const { t, locale } = useI18n()
  if (!devClock) return null
  const time = new Intl.DateTimeFormat(locale, {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: DISPLAY_TIME_ZONE,
    timeZoneName: 'short',
  }).format(now)
  return (
    <p className="dev-banner" role="status">
      {t('dev.clock', { time })}
    </p>
  )
}
