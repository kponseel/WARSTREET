import type { SupabaseClient } from '@supabase/supabase-js'
import type { MessageKey } from '../i18n/en'
import type { Vars } from '../i18n/translate'
import { logEvent } from './log'
import { rpcErrorMessage } from './rpcError'

/** A server refusal, already turned into an i18n key + variables. */
export class RpcFailure extends Error {
  readonly key: MessageKey
  readonly vars: Vars

  constructor(key: MessageKey, vars: Vars = {}) {
    super(key)
    this.name = 'RpcFailure'
    this.key = key
    this.vars = vars
  }
}

export function toFailure(error: unknown): RpcFailure {
  if (error instanceof RpcFailure) return error
  if (typeof error === 'object' && error !== null && 'message' in error) {
    const { message, details } = error as { message?: unknown; details?: unknown }
    const { key, vars } = rpcErrorMessage({
      message: typeof message === 'string' ? message : '',
      details: typeof details === 'string' ? details : null,
    })
    return new RpcFailure(key, vars)
  }
  return new RpcFailure('error.unknown')
}

/** Calls a player RPC (ARCHITECTURE §5); a refusal throws an RpcFailure. */
export async function callRpc<T>(
  client: SupabaseClient,
  fn: string,
  args: Record<string, unknown> = {},
): Promise<T> {
  const started = performance.now()
  const result = await client.rpc(fn, args)
  const ms = Math.round(performance.now() - started)
  if (result.error) {
    const failure = toFailure(result.error)
    logEvent('warn', 'rpc', `${fn} refused: ${result.error.message}`, {
      ms,
      key: failure.key,
      vars: failure.vars,
      args,
    })
    throw failure
  }
  logEvent('debug', 'rpc', `${fn} ok`, { ms })
  return result.data as T
}
