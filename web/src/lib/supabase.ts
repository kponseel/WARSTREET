import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import { readSupabaseEnv } from '../config'

let client: SupabaseClient | null | undefined

// Lazily created. PKCE flow: the login code comes back as ?code=…, which does not clash
// with HashRouter's #/… routes (ARCHITECTURE §5).
export function getSupabase(): SupabaseClient | null {
  if (client !== undefined) return client
  const env = readSupabaseEnv()
  client = env ? createClient(env.url, env.anonKey, { auth: { flowType: 'pkce' } }) : null
  return client
}
