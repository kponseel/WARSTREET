import { useNow } from '../data/clockContext'
import { useI18n } from '../i18n/context'
import { formatInstant, remaining } from '../lib/format'

/** Time left until `to` (server clock), with the deadline in Paris time. */
export function Countdown({ to, label }: { to: string; label: string }) {
  const now = useNow(1000)
  const { t, locale } = useI18n()
  const left = remaining(now.getTime(), new Date(to).getTime())
  const over = left.days + left.hours + left.minutes + left.seconds === 0
  const text = over
    ? t('countdown.over')
    : left.days > 0
      ? t('countdown.days', { d: left.days, h: left.hours, m: left.minutes })
      : t('countdown.hours', { h: left.hours, m: left.minutes, s: left.seconds })
  return (
    <p className="countdown">
      <span className="countdown-label">{label}</span>{' '}
      <strong>{text}</strong>{' '}
      <time className="muted" dateTime={to}>
        ({formatInstant(locale, to)})
      </time>
    </p>
  )
}
