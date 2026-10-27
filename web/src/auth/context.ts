import type { Session, SupabaseClient } from '@supabase/supabase-js'
import { createContext, useContext } from 'react'

export interface AuthValue {
  /** null when the build has no Supabase variables. */
  client: SupabaseClient | null
  session: Session | null
  /** True until the stored session has been read. */
  loading: boolean
  signOut: () => Promise<void>
}

export const AuthContext = createContext<AuthValue | null>(null)

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>')
  return value
}
