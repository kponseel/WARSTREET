import { useEffect, useRef, useState, type ReactNode } from 'react'
import { CommanderEmblem } from '../components/CommanderEmblem'
import { commanderExample } from '../components/commanderExample'
import { commanderName } from '../components/commanderText'
import { GAME_NAME } from '../config'
import { EXAMPLES } from '../content/examples.generated'
import { GAME_CONFIG_VALUES } from '../content/gameConfig.generated'
import { GameConfig } from '../data/gameConfig'
import { useI18n } from '../i18n/context'
import type { MessageKey } from '../i18n/en'
import { formatList, formatNumber, formatSigned, formatSignedPercent } from '../lib/format'
import { dismissTutorial, markTutorialSeen } from './tutorialState'

// Public content: rule values from the build-time copy of engine/config.py, worked
// examples from engine/examples.py. Nothing is computed here.
const CONFIG = GameConfig.fromValues(GAME_CONFIG_VALUES)
const STEPS = ['welcome', 'pf', 'squad', 'week', 'credits', 'campaign', 'commanders'] as const
type Step = (typeof STEPS)[number]

const TITLE: Record<Step, MessageKey> = {
  welcome: 'tutorial.welcome.title',
  pf: 'tutorial.pf.title',
  squad: 'tutorial.squad.title',
  week: 'tutorial.week.title',
  credits: 'tutorial.credits.title',
  campaign: 'tutorial.campaign.title',
  commanders: 'tutorial.commanders.title',
}

/** "23:59:59" → "23:59" (Paris time, as stored in game_config). */
const hhmm = (value: unknown) => (typeof value === 'string' ? value.slice(0, 5) : '')

function StepBody({ step }: { step: Step }): ReactNode {
  const { t, locale } = useI18n()
  const n = (value: number) => formatNumber(locale, value)
  const slot = (code: string) => n(CONFIG.numIn('slot_multipliers', code))
  switch (step) {
    case 'welcome':
      return (
        <>
          <p>{t('tutorial.welcome.1')}</p>
          <p>{t('tutorial.welcome.2')}</p>
          <p>{t('tutorial.welcome.3', { weeks: n(CONFIG.num('campaign_weeks_default')) })}</p>
        </>
      )
    case 'pf':
      return (
        <>
          <p>{t('tutorial.pf.1')}</p>
          <p>{t('tutorial.pf.2', { per: n(CONFIG.num('pf_per_percent')) })}</p>
          <h2>{t('tutorial.pf.example')}</h2>
          <ul className="tutorial-example">
            {EXAMPLES.week.map((unit) => (
              <li key={unit.slot}>
                {t('tutorial.pf.line', {
                  slot: t(`slot.${unit.slot}` as MessageKey),
                  mult: slot(unit.slot),
                  name: unit.name,
                  move: formatSignedPercent(locale, unit.move),
                  pf: formatSigned(locale, unit.pf),
                })}
              </li>
            ))}
            <li className="tutorial-total">
              {t('tutorial.pf.total', { total: formatSigned(locale, EXAMPLES.weekUnitsTotal) })}
            </li>
          </ul>
          <p>
            {t('tutorial.pf.3', {
              elite: n(CONFIG.num('elite_unit_bonus')),
              victory: n(CONFIG.numIn('feats', 'total_victory')),
            })}
          </p>
          <p>{t('tutorial.pf.4')}</p>
        </>
      )
    case 'squad':
      return (
        <>
          <p>
            {t('tutorial.squad.1', {
              champion: slot('champion'),
              veteran: slot('veteran'),
              priority: slot('priority_target'),
              marksman: slot('marksman'),
              saboteur: slot('saboteur'),
            })}
          </p>
          <p>{t('tutorial.squad.2')}</p>
          <p>
            {t('tutorial.squad.3', {
              front: n(CONFIG.num('front_min_per_region')),
              reserve: n(CONFIG.num('reserve_size')),
            })}
          </p>
          <p>{t('tutorial.squad.4')}</p>
          <p>{t('tutorial.squad.5', { suggest: t('briefing.suggest') })}</p>
        </>
      )
    case 'week':
      return (
        <>
          <ol className="tutorial-week">
            <li>{t('tutorial.week.briefing', { lock: hhmm(CONFIG.raw('lock_local_time')) })}</li>
            <li>{t('tutorial.week.s1')}</li>
            <li>{t('tutorial.week.resupply', { close: hhmm(CONFIG.raw('resupply_close_local_time')) })}</li>
            <li>{t('tutorial.week.s2')}</li>
            <li>{t('tutorial.week.debrief')}</li>
          </ol>
          <p>
            {t('tutorial.week.example', {
              out: EXAMPLES.swapOut,
              in: EXAMPLES.swapIn,
              before: formatSigned(locale, EXAMPLES.swapBefore),
              after: formatSigned(locale, EXAMPLES.swapAfter),
            })}
          </p>
        </>
      )
    case 'credits':
      return (
        <>
          <p>{t('tutorial.credits.1', { income: n(CONFIG.num('ammo_income')), cap: n(CONFIG.num('ammo_cap')) })}</p>
          <p>{t('tutorial.credits.2')}</p>
          <p>
            {t('tutorial.credits.3', {
              attacks: n(CONFIG.num('attack_cap_per_week')),
              bounty: n(CONFIG.num('bounty_discount')),
            })}
          </p>
          <p>{t('tutorial.credits.4')}</p>
        </>
      )
    case 'campaign': {
      const table = CONFIG.raw('campaign_points') as Record<string, number[]> | undefined
      return (
        <>
          <p>{t('tutorial.campaign.1', { points: formatList(locale, (table?.['4'] ?? []).map(n)) })}</p>
          <p>{t('tutorial.campaign.2', { final: n(CONFIG.num('final_week_multiplier')) })}</p>
          <p>{t('tutorial.campaign.3')}</p>
          <p>{t('tutorial.campaign.4', { rusty: t('badge.rusty') })}</p>
        </>
      )
    }
    case 'commanders':
      return (
        <>
          <p>{t('tutorial.commanders.1')}</p>
          <p>{t('tutorial.commanders.2')}</p>
          <ul className="tutorial-commanders">
            {CONFIG.strings('commanders').map((code) => {
              const text = commanderExample(t, locale, CONFIG, code)
              return (
                <li key={code}>
                  <p className="tutorial-commander-head">
                    <CommanderEmblem code={code} />
                    <strong>{commanderName(t, code)}</strong>
                  </p>
                  <p>{text.summary}</p>
                  <details>
                    <summary>{t('commander.example')}</summary>
                    <p>{text.example}</p>
                  </details>
                </li>
              )
            })}
          </ul>
        </>
      )
  }
}

/**
 * How to play, in 7 short steps. `auto`: shown by itself at launch, with the
 * "don't show again" box (ticked by default); from the Help link it is just a page.
 */
export function Tutorial({ auto = false, onDone }: { auto?: boolean; onDone: () => void }) {
  const { t } = useI18n()
  const [index, setIndex] = useState(0)
  const [dontShow, setDontShow] = useState(true)
  const heading = useRef<HTMLHeadingElement>(null)
  const moved = useRef(false)
  useEffect(() => {
    // Move focus to the new step's title (not on first render: the page keeps its focus).
    if (moved.current) heading.current?.focus()
  }, [index])
  const step = STEPS[index] ?? 'welcome'
  const last = index === STEPS.length - 1
  const go = (next: number) => {
    moved.current = true
    setIndex(next)
    window.scrollTo(0, 0)
  }
  const finish = () => {
    if (auto && dontShow) dismissTutorial()
    markTutorialSeen()
    window.scrollTo(0, 0)
    onDone()
  }
  return (
    <section className="page tutorial" aria-labelledby="tutorial-title">
      <p className="tutorial-progress">
        {t('tutorial.label')} · {t('tutorial.step', { n: index + 1, total: STEPS.length })}
      </p>
      <h1 id="tutorial-title" ref={heading} tabIndex={-1}>
        {t(TITLE[step], { game: GAME_NAME })}
      </h1>
      <div className="tutorial-body">
        <StepBody step={step} />
      </div>
      <div className="tutorial-nav">
        {index > 0 && (
          <button
            type="button"
            className="button button-secondary"
            onClick={() => {
              go(index - 1)
            }}
          >
            {t('tutorial.back')}
          </button>
        )}
        {last ? (
          <button type="button" className="button" onClick={finish}>
            {t('tutorial.finish')}
          </button>
        ) : (
          <button
            type="button"
            className="button"
            onClick={() => {
              go(index + 1)
            }}
          >
            {t('tutorial.next')}
          </button>
        )}
      </div>
      {auto && (
        <label className="tutorial-dont-show">
          <input
            type="checkbox"
            checked={dontShow}
            onChange={(e) => {
              setDontShow(e.target.checked)
            }}
          />{' '}
          {t('tutorial.dontShow')}
        </label>
      )}
      {!last && (
        <button type="button" className="button-link tutorial-skip" onClick={finish}>
          {t('tutorial.skip')}
        </button>
      )}
    </section>
  )
}
