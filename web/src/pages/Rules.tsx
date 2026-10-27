import { CommanderEmblem } from '../components/CommanderEmblem'
import { commanderText } from '../components/commanderText'
import { GAME_CONFIG_VALUES } from '../content/gameConfig.generated'
import { rulesEn } from '../content/rules.en'
import { rulesFr } from '../content/rules.fr'
import { fillRuleText } from '../content/fillRuleText'
import { GameConfig } from '../data/gameConfig'
import { useI18n } from '../i18n/context'

const CONTENT = { en: rulesEn, fr: rulesFr }
// Public page: the values come from the build-time copy of engine/config.py.
const CONFIG = GameConfig.fromValues(GAME_CONFIG_VALUES)
const NUMBERS = CONFIG.numbers()

export function Rules() {
  const { t, locale } = useI18n()
  const content = CONTENT[locale]
  const fill = (text: string) => fillRuleText(locale, text, NUMBERS)
  return (
    <article className="page rules">
      <h1>{t('rules.title')}</h1>
      <p className="lead">{fill(content.intro)}</p>
      <nav aria-label={t('rules.contents')}>
        <ul className="toc">
          {content.sections.map((s) => (
            <li key={s.id}>
              <a href={`#/rules`} onClick={(e) => {
                e.preventDefault()
                document.getElementById(`rules-${s.id}`)?.scrollIntoView()
              }}>
                {s.title}
              </a>
            </li>
          ))}
        </ul>
      </nav>
      {content.sections.map((section) => (
        <section key={section.id} id={`rules-${section.id}`} aria-labelledby={`rules-${section.id}-h`}>
          <h2 id={`rules-${section.id}-h`}>{section.title}</h2>
          {section.paragraphs.map((p) => (
            <p key={p}>{fill(p)}</p>
          ))}
          {section.id === 'commanders' && (
            <ul className="commander-list">
              {CONFIG.strings('commanders').map((code) => {
                const text = commanderText(t, locale, CONFIG, code)
                return (
                  <li key={code} className="card">
                    <h3 className="choice-card-head">
                      <CommanderEmblem code={code} />
                      {text.name}
                    </h3>
                    <p>
                      <span className="choice-card-label">{t('commander.passive')}</span>{' '}
                      {text.passive}
                    </p>
                    <p>
                      <span className="choice-card-label">{t('commander.constraint')}</span>{' '}
                      {text.constraint}
                    </p>
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      ))}
      <section aria-labelledby="rules-glossary-h">
        <h2 id="rules-glossary-h">{t('rules.glossary')}</h2>
        <dl className="glossary">
          {content.glossary.map((entry) => (
            <div key={entry.term}>
              <dt>{t(entry.term)}</dt>
              <dd>{entry.text}</dd>
            </div>
          ))}
        </dl>
      </section>
    </article>
  )
}
