import type { GameConfig } from '../data/gameConfig'
import { useI18n } from '../i18n/context'
import { ColorPicker } from './ColorPicker'
import { CommanderPicker } from './CommanderPicker'
import type { MemberDraft } from './memberDraft'

/** Pseudo, commander and avatar colour (create, join and lobby forms). */
export function MemberFields({
  config,
  draft,
  onChange,
  idPrefix,
}: {
  config: GameConfig
  draft: MemberDraft
  onChange: (draft: MemberDraft) => void
  idPrefix: string
}) {
  const { t } = useI18n()
  const min = config.num('pseudo_min_length')
  const max = config.num('pseudo_max_length')
  // The Drone's colour (the last one) is not offered to humans.
  const colors = config.strings('avatar_colors').slice(0, -1)
  return (
    <>
      <div className="field">
        <label htmlFor={`${idPrefix}-pseudo`}>{t('member.pseudo')}</label>
        <input
          id={`${idPrefix}-pseudo`}
          name="pseudo"
          required
          minLength={min}
          maxLength={max}
          autoComplete="nickname"
          value={draft.pseudo}
          aria-describedby={`${idPrefix}-pseudo-hint`}
          onChange={(e) => {
            onChange({ ...draft, pseudo: e.target.value })
          }}
        />
        <p id={`${idPrefix}-pseudo-hint`} className="hint">
          {t('member.pseudoHint', { min, max })}
        </p>
      </div>
      <CommanderPicker
        config={config}
        name={`${idPrefix}-commander`}
        value={draft.commander}
        onChange={(commander) => {
          onChange({ ...draft, commander })
        }}
      />
      <ColorPicker
        colors={colors}
        name={`${idPrefix}-color`}
        value={draft.color}
        onChange={(color) => {
          onChange({ ...draft, color })
        }}
      />
    </>
  )
}
