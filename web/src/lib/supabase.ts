import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import { readSupabaseEnv } from '../config'

let client: SupabaseClient | null | undefined

// Lazily created. PKCE flow: the login code comes back as ?code=…, which does not clash
// with HashRouter's #/… routes (ARCHITECTURE §5). The app exchanges it itself before the
// router mounts (lib/auth.ts), so the client must not look at the URL on its own.
export function getSupabase(): SupabaseClient | null {
  if (client !== undefined) return client
  const env = readSupabaseEnv()
  client = env
    ? createClient(env.url, env.anonKey, {
        auth: { flowType: 'pkce', detectSessionInUrl: false, persistSession: true },
      })
    : null
  return client
}

// Tests only: install a fake client (or none).
export function setSupabaseForTests(fake: SupabaseClient | null | undefined): void {
  client = fake
}
