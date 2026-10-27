import type { GameConfig } from '../data/gameConfig'
import { useI18n } from '../i18n/context'
import { CommanderEmblem } from './CommanderEmblem'
import { commanderText } from './commanderText'

export function CommanderPicker({
  config,
  value,
  onChange,
  name = 'commander',
}: {
  config: GameConfig
  value: string | null
  onChange: (code: string) => void
  name?: string
}) {
  const { t, locale } = useI18n()
  return (
    <fieldset className="choice-grid commander-picker">
      <legend>{t('member.commander')}</legend>
      {config.strings('commanders').map((code) => {
        const text = commanderText(t, locale, config, code)
        const id = `${name}-${code}`
        return (
          <label key={code} className="choice-card" htmlFor={id}>
            <input
              id={id}
              type="radio"
              name={name}
              value={code}
              checked={value === code}
              onChange={() => {
                onChange(code)
              }}
            />
            <span className="choice-card-head">
              <CommanderEmblem code={code} />
              <strong>{text.name}</strong>
            </span>
            <span className="choice-card-line">
              <span className="choice-card-label">{t('commander.passive')}</span> {text.passive}
            </span>
            <span className="choice-card-line">
              <span className="choice-card-label">{t('commander.constraint')}</span>{' '}
              {text.constraint}
            </span>
          </label>
        )
      })}
    </fieldset>
  )
}
