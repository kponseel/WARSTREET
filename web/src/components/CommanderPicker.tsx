import { Link } from 'react-router'
import type { GameConfig } from '../data/gameConfig'
import { useI18n } from '../i18n/context'
import { formatNumber } from '../lib/format'
import { CommanderEmblem } from './CommanderEmblem'
import { commanderExample } from './commanderExample'
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
      <p className="hint commander-hint">
        {t('commander.pfHint', { per: formatNumber(locale, config.num('pf_per_percent')) })}{' '}
        <Link to="/tutorial">{t('commander.pfHintLink')}</Link>
      </p>
      {config.strings('commanders').map((code) => {
        const text = commanderText(t, locale, config, code)
        const example = commanderExample(t, locale, config, code)
        const id = `${name}-${code}`
        return (
          // The example sits outside the <label>: opening it never picks the commander,
          // and the radio's name stays the commander's text.
          <div key={code} className="choice-card">
            <label className="choice-card-main" htmlFor={id}>
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
              <span className="choice-card-line">{example.summary}</span>
              <span className="choice-card-line">
                <span className="choice-card-label">{t('commander.passive')}</span> {text.passive}
              </span>
              <span className="choice-card-line">
                <span className="choice-card-label">{t('commander.constraint')}</span>{' '}
                {text.constraint}
              </span>
            </label>
            <details className="choice-card-example">
              <summary>{t('commander.example')}</summary>
              <p>{example.example}</p>
            </details>
          </div>
        )
      })}
    </fieldset>
  )
}
