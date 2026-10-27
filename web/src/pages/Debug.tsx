import { useEffect, useState, useSyncExternalStore } from 'react'
import { useAuth } from '../auth/context'
import { useClock } from '../data/clockContext'
import { useI18n } from '../i18n/context'
import { clearLog, isDebug, logEntries, setDebug, subscribeLog, type LogLevel } from '../lib/log'

const LEVELS: LogLevel[] = ['debug', 'info', 'warn', 'error']

function useLog() {
  return useSyncExternalStore(subscribeLog, () => logEntries().length + (isDebug() ? 0.5 : 0))
}

/** #/debug: what this tab did, the clocks, the build and the server status (bug reports). */
export function Debug() {
  useLog()
  const { t } = useI18n()
  const { client, session } = useAuth()
  const { offsetMs, devClock } = useClock()
  const [minLevel, setMinLevel] = useState<LogLevel>('debug')
  const [status, setStatus] = useState<Record<string, unknown> | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!client || !session) return
    void client
      .from('system_status')
      .select('*')
      .maybeSingle()
      .then(({ data }) => {
        setStatus((data as Record<string, unknown> | null) ?? null)
      })
  }, [client, session])

  const entries = logEntries().filter((e) => LEVELS.indexOf(e.level) >= LEVELS.indexOf(minLevel))
  const report = {
    build: import.meta.env.VITE_APP_COMMIT ?? 'dev',
    url: window.location.hash,
    userId: session?.user.id ?? null,
    deviceTime: new Date().toISOString(),
    serverOffsetMs: Math.round(offsetMs),
    devClock,
    status,
    userAgent: navigator.userAgent,
    log: logEntries(),
  }

  return (
    <section className="page debug">
      <h1>{t('debug.title')}</h1>
      <p className="muted">{t('debug.intro')}</p>
      <div className="row">
        <button
          type="button"
          className="button button-secondary"
          aria-pressed={isDebug()}
          onClick={() => {
            setDebug(!isDebug())
          }}
        >
          {t(isDebug() ? 'debug.disable' : 'debug.enable')}
        </button>
        <button
          type="button"
          className="button"
          onClick={() => {
            void navigator.clipboard.writeText(JSON.stringify(report, null, 2)).then(() => {
              setCopied(true)
            })
          }}
        >
          {t('debug.copy')}
          <span className="sr-live" aria-live="polite">
            {copied ? ` · ${t('common.copied')}` : ''}
          </span>
        </button>
        <button type="button" className="button button-link" onClick={clearLog}>
          {t('debug.clear')}
        </button>
      </div>
      <dl className="debug-facts">
        <div>
          <dt>{t('debug.build')}</dt>
          <dd>{report.build}</dd>
        </div>
        <div>
          <dt>{t('debug.user')}</dt>
          <dd>{report.userId ?? '—'}</dd>
        </div>
        <div>
          <dt>{t('debug.offset')}</dt>
          <dd>
            {report.serverOffsetMs} ms{devClock ? ` · ${t('debug.devClock')}` : ''}
          </dd>
        </div>
        <div>
          <dt>{t('debug.lastTick')}</dt>
          <dd>{typeof status?.last_tick_at === 'string' ? status.last_tick_at : '—'}</dd>
        </div>
      </dl>
      <div className="field">
        <label htmlFor="debug-level">{t('debug.level')}</label>
        <select
          id="debug-level"
          value={minLevel}
          onChange={(e) => {
            setMinLevel(e.target.value as LogLevel)
          }}
        >
          {LEVELS.map((level) => (
            <option key={level} value={level}>
              {level}
            </option>
          ))}
        </select>
      </div>
      {entries.length === 0 ? (
        <p className="muted">{t('debug.empty')}</p>
      ) : (
        <ol className="debug-log" reversed>
          {[...entries].reverse().map((e, i) => (
            <li key={`${e.ts}-${String(i)}`} className={`log-${e.level}`}>
              <code>
                {e.ts.slice(11, 19)} {e.level} [{e.scope}] {e.message}
                {e.data ? ` ${JSON.stringify(e.data)}` : ''}
              </code>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
