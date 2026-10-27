import { useCallback, useState } from 'react'
import { RpcFailure, toFailure } from './rpc'

/** Runs one user action at a time; keeps its pending state and its translated error. */
export function useAction(): {
  pending: boolean
  error: RpcFailure | null
  run: (action: () => Promise<void>) => Promise<boolean>
  clear: () => void
} {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<RpcFailure | null>(null)
  const run = useCallback(async (action: () => Promise<void>) => {
    setPending(true)
    setError(null)
    try {
      await action()
      return true
    } catch (caught) {
      setError(toFailure(caught))
      return false
    } finally {
      setPending(false)
    }
  }, [])
  const clear = useCallback(() => {
    setError(null)
  }, [])
  return { pending, error, run, clear }
}
