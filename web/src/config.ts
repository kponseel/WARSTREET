// The game name lives here and in engine/engine/config.py only. Never hardcode it elsewhere.
export const GAME_NAME = 'WARSTREET'

export interface SupabaseEnv {
  url: string
  anonKey: string
}

// Public by design (anon key). Returns null when the build has no Supabase variables,
// so the app still builds and shows a "not configured" state.
export function readSupabaseEnv(): SupabaseEnv | null {
  const url: unknown = import.meta.env.VITE_SUPABASE_URL
  const anonKey: unknown = import.meta.env.VITE_SUPABASE_ANON_KEY
  if (typeof url !== 'string' || typeof anonKey !== 'string' || url === '' || anonKey === '') {
    return null
  }
  return { url, anonKey }
}

// Length of the email login code. Must match Supabase Auth → Email OTP length (default 6).
export const LOGIN_CODE_LENGTH = 6
