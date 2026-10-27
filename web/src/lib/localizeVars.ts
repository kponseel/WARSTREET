import type { MessageKey } from '../i18n/en'
import { en } from '../i18n/en'
import type { Vars } from '../i18n/translate'

/** Server variables that are codes (a slot) become labels in the reader's language. */
export function localizeVars(t: (key: MessageKey, vars?: Vars) => string, vars: Vars | undefined): Vars {
  if (!vars) return {}
  const result: Vars = { ...vars }
  const slot = vars.slot
  if (typeof slot === 'string' && `slot.${slot}` in en) result.slot = t(`slot.${slot}` as MessageKey)
  return result
}
