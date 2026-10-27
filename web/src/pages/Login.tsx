import { useState, type SyntheticEvent } from 'react'
import { Navigate } from 'react-router'
import { useAuth } from '../auth/context'
import { LOGIN_CODE_LENGTH } from '../config'
import { useI18n } from '../i18n/context'
import type { MessageKey } from '../i18n/en'
import {
  appUrl,
  isValidCode,
  peekPendingPath,
  sendLoginEmail,
  takeLoginProblem,
  verifyLoginCode,
} from '../lib/auth'

type Step = { name: 'email' } | { name: 'code'; email: string }

function authErrorKey(code: string): MessageKey {
  if (code === 'over_email_send_rate_limit' || code === 'over_request_rate_limit') {
    return 'login.error.rateLimit'
  }
  if (code === 'otp_expired' || code === 'invalid_credentials') return 'login.error.badCode'
  return 'login.error.generic'
}

export function Login() {
  const { client, session, loading } = useAuth()
  const { t, locale } = useI18n()
  const [step, setStep] = useState<Step>({ name: 'email' })
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<MessageKey | null>(() =>
    takeLoginProblem() ? 'login.error.linkInvalid' : null,
  )
  const [sentAgain, setSentAgain] = useState(false)

  if (!client) {
    return (
      <section className="page">
        <h1>{t('login.title')}</h1>
        <p className="status status-missing">{t('home.backend.missing')}</p>
      </section>
    )
  }
  if (!loading && session) {
    return <Navigate to={peekPendingPath() ?? '/'} replace />
  }

  const send = async (address: string) => {
    setPending(true)
    setError(null)
    const result = await sendLoginEmail(client, address, locale, appUrl(window.location))
    setPending(false)
    if (result.error) {
      setError(authErrorKey(result.error))
      return false
    }
    return true
  }

  const onEmail = async (event: SyntheticEvent) => {
    event.preventDefault()
    const address = email.trim()
    if (await send(address)) {
      setStep({ name: 'code', email: address })
      setSentAgain(false)
    }
  }

  const onCode = async (event: SyntheticEvent) => {
    event.preventDefault()
    if (step.name !== 'code') return
    if (!isValidCode(code, LOGIN_CODE_LENGTH)) {
      setError('login.error.codeFormat')
      return
    }
    setPending(true)
    setError(null)
    const result = await verifyLoginCode(client, step.email, code)
    setPending(false)
    if (result.error) setError(authErrorKey(result.error))
    // On success the session changes and this page redirects.
  }

  return (
    <section className="page narrow">
      <h1>{t('login.title')}</h1>
      {step.name === 'email' ? (
        <form className="form" onSubmit={(e) => void onEmail(e)}>
          <p>{t('login.intro')}</p>
          <div className="field">
            <label htmlFor="login-email">{t('login.email')}</label>
            <input
              id="login-email"
              type="email"
              name="email"
              required
              autoComplete="email"
              inputMode="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value)
              }}
            />
          </div>
          {error && (
            <p className="error" role="alert">
              {t(error)}
            </p>
          )}
          <button type="submit" className="button" disabled={pending}>
            {t('login.send')}
          </button>
        </form>
      ) : (
        <form className="form" onSubmit={(e) => void onCode(e)}>
          <p role="status">{t('login.sent', { email: step.email })}</p>
          <div className="field">
            <label htmlFor="login-code">{t('login.code', { n: LOGIN_CODE_LENGTH })}</label>
            <input
              id="login-code"
              name="code"
              required
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={LOGIN_CODE_LENGTH}
              value={code}
              onChange={(e) => {
                setCode(e.target.value.replace(/\D/g, ''))
              }}
            />
          </div>
          {error && (
            <p className="error" role="alert">
              {t(error)}
            </p>
          )}
          <button type="submit" className="button" disabled={pending}>
            {t('login.verify')}
          </button>
          <div className="row">
            <button
              type="button"
              className="button button-link"
              disabled={pending}
              onClick={() => {
                void send(step.email).then((ok) => {
                  setSentAgain(ok)
                })
              }}
            >
              {t('login.resend')}
            </button>
            <button
              type="button"
              className="button button-link"
              onClick={() => {
                setStep({ name: 'email' })
                setCode('')
                setError(null)
              }}
            >
              {t('login.changeEmail')}
            </button>
          </div>
          {sentAgain && <p role="status">{t('login.sentAgain')}</p>}
        </form>
      )}
    </section>
  )
}
