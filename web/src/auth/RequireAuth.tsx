import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import { useI18n } from '../i18n/context'
import { savePendingPath } from '../lib/auth'
import { useAuth } from './context'

/** Pages for logged-in players. Others go to the login page and come back afterwards. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { client, session, loading } = useAuth()
  const { t } = useI18n()
  const location = useLocation()
  if (!client) {
    return <p className="status status-missing">{t('home.backend.missing')}</p>
  }
  if (loading) {
    return <p aria-busy="true">{t('common.loading')}</p>
  }
  if (!session) {
    savePendingPath(location.pathname)
    return <Navigate to="/login" replace />
  }
  return children
}
