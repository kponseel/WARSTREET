import { useNow } from '../data/clockContext'
import { useI18n } from '../i18n/context'
import { formatInstant } from '../lib/format'
import { dailyPhase, type Session } from './dailyPhase'

export function PhaseBanner({ sessions }: { sessions: Session[] }) {
  const { t, locale } = useI18n()
  const now = useNow(30_000)
  const { phase, next } = dailyPhase(now, sessions)
  return (
    <div className={`phase-banner phase-${phase}`} role="status">
      <strong>{t(`phase.${phase}`)}</strong>
      {next && (
        <span>
          {' '}
          · {t('phase.next', { time: formatInstant(locale, next.toISOString()) })}
        </span>
      )}
    </div>
  )
}
