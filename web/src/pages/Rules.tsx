import { CommanderEmblem } from '../components/CommanderEmblem'
import { commanderName, commanderText } from '../components/commanderText'
import { GAME_CONFIG_VALUES } from '../content/gameConfig.generated'
import { rulesEn } from '../content/rules.en'
import { rulesFr } from '../content/rules.fr'
import { fillRuleText } from '../content/fillRuleText'
import { GameConfig } from '../data/gameConfig'
import { orderDescription } from '../briefing/orderText'
import { useI18n } from '../i18n/context'
import type { MessageKey } from '../i18n/en'
import { formatList, formatNumber } from '../lib/format'
import { GuideI18n, type T } from '../i18n/guide'
import type { ReactNode } from 'react'

const CONTENT = { en: rulesEn, fr: rulesFr }
// Public page: the values come from the build-time copy of engine/config.py.
const CONFIG = GameConfig.fromValues(GAME_CONFIG_VALUES)
const NUMBERS = CONFIG.numbers()
// Every order with its kind, cost and windows (game_config), attacks first.
const KIND_ORDER = ['attack', 'defense', 'maneuver']
type OrderInfo = { kind: string; cost: number; windows: string[] }
const ORDERS = Object.entries((CONFIG.raw('orders') ?? {}) as Record<string, OrderInfo>).sort(
  ([a, x], [b, y]) => KIND_ORDER.indexOf(x.kind) - KIND_ORDER.indexOf(y.kind) || a.localeCompare(b),
)

/** The rules, in the guides' language (EN/FR switch at the top, like Help). */
export function Rules() {
  return <GuideI18n>{(ui, languageSwitch) => <RulesView ui={ui} languageSwitch={languageSwitch} />}</GuideI18n>
}

// Names the player sees on screen (commanders, glossary terms) come from `ui`, the app's language.
function RulesView({ ui, languageSwitch }: { ui: T; languageSwitch: ReactNode }) {
  const { t, locale } = useI18n()
  const content = CONTENT[locale]
  const fill = (text: string) => fillRuleText(locale, text, NUMBERS)
  return (
    <article className="page rules" lang={locale}>
      {languageSwitch}
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
                const text = commanderText(t, locale, CONFIG, code, ui)
                return (
                  <li key={code} className="card">
                    <h3 className="choice-card-head">
                      <CommanderEmblem code={code} />
                      {commanderName(ui, code)}
                    </h3>
                    <p>
                      <span className="choice-card-label">{t('commander.passive')}</span>{' '}
                      {text.passive}
                    </p>
                    {text.constraint && (
                      <p>
                        <span className="choice-card-label">{t('commander.constraint')}</span>{' '}
                        {text.constraint}
                      </p>
                    )}
                  </li>
                )
              })}
            </ul>
          )}
          {section.id === 'orders' && (
            <ul className="commander-list">
              {ORDERS.map(([code, order]) => (
                <li key={code} className="card">
                  <h3>{ui(`order.${code}` as MessageKey)}</h3>
                  <p className="muted">
                    {t('rules.orderFacts', {
                      kind: t(`orders.kind.${order.kind}` as MessageKey),
                      cost: formatNumber(locale, order.cost),
                      when: formatList(
                        locale,
                        order.windows.map((w) => ui(`nav.league.${w}` as MessageKey)),
                        'disjunction',
                      ),
                    })}
                  </p>
                  <p>{orderDescription(t, CONFIG, code)}</p>
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}
      <section aria-labelledby="rules-glossary-h">
        <h2 id="rules-glossary-h">{t('rules.glossary')}</h2>
        <dl className="glossary">
          {content.glossary.map((entry) => (
            <div key={entry.term}>
              <dt>{ui(entry.term)}</dt>
              <dd>{entry.text}</dd>
            </div>
          ))}
        </dl>
      </section>
    </article>
  )
}
