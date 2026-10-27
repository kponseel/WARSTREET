import { useI18n } from '../i18n/context'
import { localizeVars } from '../lib/localizeVars'
import type { RpcFailure } from '../lib/rpc'

export function ErrorMessage({ error }: { error: RpcFailure | null }) {
  const { t } = useI18n()
  if (!error) return null
  return (
    <p className="error" role="alert">
      {t(error.key, localizeVars(t, error.vars))}
    </p>
  )
}
