import { useI18n } from '../i18n/context'
import type { MessageKey } from '../i18n/en'

/** Badges next to a pseudo (GAME_RULES §8), with their meaning as a tooltip. */
export function BadgeChips({ codes }: { codes: readonly string[] }) {
  const { t } = useI18n()
  if (codes.length === 0) return null
  return (
    <span className="badge-chips">
      {codes.map((code) => (
        <span key={code} className={`badge badge-${code}`} title={t(`badge.${code}.desc` as MessageKey)}>
          {t(`badge.${code}` as MessageKey)}
        </span>
      ))}
    </span>
  )
}
