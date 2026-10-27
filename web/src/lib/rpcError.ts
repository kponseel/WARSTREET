import { en, type MessageKey } from '../i18n/en'
import type { Vars } from '../i18n/translate'

// RPC errors come back from PostgREST as { message: CODE, details: JSON vars }
// (supabase/migrations, private.raise_error). This turns one into a message key + variables.
export interface RpcErrorLike {
  message?: string
  details?: string | null
}

function isVars(value: unknown): value is Vars {
  return (
    typeof value === 'object' &&
    value !== null &&
    Object.values(value).every((v) => typeof v === 'string' || typeof v === 'number')
  )
}

export function rpcErrorMessage(error: RpcErrorLike): { key: MessageKey; vars: Vars } {
  const key = `error.${error.message ?? ''}`
  if (!(key in en)) return { key: 'error.unknown', vars: {} }
  let vars: Vars = {}
  try {
    const parsed: unknown = error.details ? JSON.parse(error.details) : {}
    if (isVars(parsed)) vars = parsed
  } catch {
    // Not JSON: keep the message without variables.
  }
  return { key: key as MessageKey, vars }
}
