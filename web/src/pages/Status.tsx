import { useEffect, useState } from 'react'
import { useAuth } from '../auth/context'
import { useI18n } from '../i18n/context'
import { formatInstant } from '../lib/format'
import { logEvent } from '../lib/log'
import { ago, health, type SystemStatus } from '../ops/status'

const REFRESH_MS = 60_000

/** #/status: is the game server running? Last tick, failures, price freshness. */
export function Status() {
  const { t, locale } = useI18n()
  const { client } = useAuth()
  const [status, setStatus] = useState<SystemStatus | null | undefined>(undefined)
  // Real time (the cron runs on it, even with the dev clock on), refreshed with the status.
  const [nowMs, setNowMs] = useState(0)

  useEffect(() => {
    if (!client) return
    const load = () => {
      void client
        .from('system_status')
        .select('last_tick_at, last_tick_ok, last_success_at, consecutive_failures, prices_updated_at, dev_clock')
        .maybeSingle()
        .then(({ data, error }) => {
          if (error) logEvent('error', 'status', error.message)
          const row: unknown = data
          setStatus((row as SystemStatus | null) ?? null)
          setNowMs(Date.now())
        })
    }
    load()
    const timer = window.setInterval(load, REFRESH_MS)
    return () => {
      window.clearInterval(timer)
    }
  }, [client])

  if (status === undefined) return <p aria-busy="true">{t('common.loading')}</p>
  const state = health(status, nowMs)
  const when = (iso: string | null) =>
    iso ? `${formatInstant(locale, iso)} (${ago(locale, iso, nowMs)})` : t('status.never')

  return (
    <section className="page status-page">
      <h1>{t('status.title')}</h1>
      <p className={`health-banner health-${state}`} role="status">
        {t(`status.health.${state}`)}
      </p>
      <dl className="status-facts">
        <dt>{t('status.lastTick')}</dt>
        <dd>{when(status?.last_tick_at ?? null)}</dd>
        <dt>{t('status.lastSuccess')}</dt>
        <dd>{when(status?.last_success_at ?? null)}</dd>
        <dt>{t('status.failures')}</dt>
        <dd>{status?.consecutive_failures ?? 0}</dd>
        <dt>{t('status.prices')}</dt>
        <dd>{when(status?.prices_updated_at ?? null)}</dd>
        {status?.dev_clock && (
          <>
            <dt>{t('status.devClock')}</dt>
            <dd>{t('status.devClockOn')}</dd>
          </>
        )}
      </dl>
      <p className="muted">{t('status.help')}</p>
    </section>
  )
}
