import type { Session, SupabaseClient } from '@supabase/supabase-js'
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useI18n } from '../i18n/context'
import { isLocale } from '../i18n/translate'
import { AuthContext, type AuthValue } from './context'

export function AuthProvider({
  client,
  children,
}: {
  client: SupabaseClient | null
  children: ReactNode
}) {
  const { setLocale, localeVersion } = useI18n()
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(client !== null)

  useEffect(() => {
    if (!client) return
    let active = true
    void client.auth.getSession().then(({ data }) => {
      if (!active) return
      setSession(data.session)
      setLoading(false)
    })
    const { data } = client.auth.onAuthStateChange((_event, next) => {
      setSession(next)
    })
    return () => {
      active = false
      data.subscription.unsubscribe()
    }
  }, [client])

  // The player's language is profiles.locale (set at sign-up from the browser language).
  const userId = session?.user.id
  useEffect(() => {
    if (!client || !userId) return
    const run = { cancelled: false }
    const before = localeVersion()
    void (async () => {
      const { data } = await client.from('profiles').select('locale').eq('id', userId).maybeSingle()
      const locale: unknown = (data as { locale?: unknown } | null)?.locale
      // A language picked while the profile loaded wins (it is being saved by set_locale).
      if (!run.cancelled && localeVersion() === before && isLocale(locale)) setLocale(locale)
    })()
    return () => {
      run.cancelled = true
    }
  }, [client, userId, setLocale, localeVersion])

  const signOut = useCallback(async () => {
    if (client) await client.auth.signOut()
  }, [client])

  const value = useMemo<AuthValue>(
    () => ({ client, session, loading, signOut }),
    [client, session, loading, signOut],
  )
  return <AuthContext value={value}>{children}</AuthContext>
}
