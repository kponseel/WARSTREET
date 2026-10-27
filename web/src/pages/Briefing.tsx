import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useAuth } from '../auth/context'
import { Catalogue } from '../briefing/Catalogue'
import { NO_FILTERS, type CatalogueFilters } from '../briefing/filters'
import { OrdersPanel } from '../briefing/OrdersPanel'
import { PactsPanel } from '../briefing/PactsPanel'
import { SlotBoard } from '../briefing/SlotBoard'
import {
  frontSlots,
  reserveSlots,
  slotKey,
  squadErrors,
  suggestSquad,
  type Squad,
} from '../briefing/squadRules'
import { useBriefing, type BriefingData } from '../briefing/useBriefing'
import { Countdown } from '../components/Countdown'
import { ErrorMessage } from '../components/ErrorMessage'
import { LeagueNav } from '../components/LeagueNav'
import { useClock, useNow } from '../data/clockContext'
import { useGameConfig, type GameConfig } from '../data/gameConfig'
import { useI18n } from '../i18n/context'
import { localizeVars } from '../lib/localizeVars'
import { callRpc } from '../lib/rpc'
import { useAction } from '../lib/useAction'

function SquadBuilder({
  data,
  config,
  open,
  onSaved,
}: {
  data: BriefingData
  config: GameConfig
  open: boolean
  onSaved: () => void
}) {
  const { t } = useI18n()
  const { client } = useAuth()
  const commander = data.me.commander
  const slots = useMemo(
    () => [...frontSlots(config), ...reserveSlots(config, commander)],
    [config, commander],
  )
  const [draft, setDraft] = useState<Squad>(() => ({ ...data.saved.units }))
  const [active, setActive] = useState<string | null>(
    () => slots.find((s) => data.saved.units[s] === undefined) ?? null,
  )
  const [filters, setFilters] = useState<CatalogueFilters>(NO_FILTERS)
  const action = useAction()
  const units = useMemo(() => new Map(data.units.map((u) => [u.id, u])), [data.units])
  const errors = squadErrors(draft, units, config, commander)
  const missing = errors.filter((e) => e.key === 'error.SQUAD_MISSING_SLOT').length
  const ruleErrors = errors.filter((e) => e.key !== 'error.SQUAD_MISSING_SLOT')
  const dirty = slots.some((s) => draft[s] !== data.saved.units[s])
  const used = new Set(Object.values(draft).filter((id): id is number => id !== undefined))
  const nextEmpty = (squad: Squad, after: string | null) =>
    slots.find((s, i) => squad[s] === undefined && (after === null || i > slots.indexOf(after))) ??
    slots.find((s) => squad[s] === undefined) ??
    null

  const catalogueUnits =
    active === 'priority_target' ? data.units.filter((u) => u.stats?.in_conflict_zone) : data.units

  const save = async () => {
    if (!client) return
    const ok = await action.run(async () => {
      await callRpc(client, 'save_squad', { p_league: data.league.id, p_units: draft })
    })
    if (ok) {
      setActive(null)
      onSaved()
    }
  }

  return (
    <section aria-labelledby="squad-h" className="squad">
      <h2 id="squad-h">{t('briefing.squad')}</h2>
      {data.saved.auto && <p className="notice">{t('briefing.autoSquad')}</p>}
      <SlotBoard
        config={config}
        commander={commander}
        squad={draft}
        units={units}
        active={active}
        editable={open}
        onSelect={setActive}
        onClear={(slot) => {
          setDraft(Object.fromEntries(Object.entries(draft).filter(([key]) => key !== slot)))
          setActive(slot)
        }}
      />
      <div className="squad-status" role="status">
        {missing > 0 ? (
          <p>{t('briefing.toPlace', { n: missing })}</p>
        ) : ruleErrors.length === 0 ? (
          <p className="ok-text">{t('briefing.valid')}</p>
        ) : null}
        {ruleErrors.length > 0 && (
          <ul className="rule-errors">
            {ruleErrors.map((e) => (
              <li key={`${e.key}-${JSON.stringify(e.vars ?? {})}`}>{t(e.key, localizeVars(t, e.vars))}</li>
            ))}
          </ul>
        )}
      </div>
      {open && (
        <div className="row">
          <button
            type="button"
            className="button"
            disabled={action.pending || errors.length > 0 || !dirty}
            onClick={() => void save()}
          >
            {t('briefing.save')}
          </button>
          <button
            type="button"
            className="button button-secondary"
            onClick={() => {
              const suggestion = suggestSquad(data.units, config, commander)
              if (suggestion) {
                setDraft(suggestion)
                setActive(null)
              }
            }}
          >
            {t('briefing.suggest')}
          </button>
          {dirty && data.saved.submittedAt && (
            <button
              type="button"
              className="button button-link"
              onClick={() => {
                setDraft({ ...data.saved.units })
              }}
            >
              {t('briefing.revert')}
            </button>
          )}
        </div>
      )}
      <p className="muted" role="status">
        {dirty
          ? t('briefing.unsaved')
          : data.saved.submittedAt
            ? t('briefing.saved')
            : t('briefing.notSaved')}
      </p>
      <ErrorMessage error={action.error} />
      {open && active === null && missing === 0 && (
        <p className="hint">{t('briefing.tapToChange')}</p>
      )}
      {open && active !== null && (
        <Catalogue
          units={catalogueUnits}
          used={used}
          slotLabel={active ? t(slotKey(active)) : null}
          filters={filters}
          onFilters={setFilters}
          onDeploy={(unit) => {
            if (!active) return
            const next = { ...draft, [active]: unit.id }
            setDraft(next)
            setActive(nextEmpty(next, active))
          }}
        />
      )}
    </section>
  )
}

export function Briefing() {
  const { id = '' } = useParams()
  const { client, session } = useAuth()
  const { t } = useI18n()
  const config = useGameConfig(client)
  const [state, refresh] = useBriefing(client, id, session?.user.id ?? '')
  const now = useNow(5000)
  const { synced } = useClock()

  if (state.status === 'loading' || !config || !synced) return <p aria-busy="true">{t('common.loading')}</p>
  if (state.status === 'error') {
    return (
      <p className="error" role="alert">
        {t('error.unknown')}
      </p>
    )
  }
  if (state.status === 'not-started') {
    return (
      <section className="page">
        <LeagueNav leagueId={id} />
        <p className="notice">{t('briefing.notStarted')}</p>
        <Link to={`/l/${id}/lobby`}>{t('nav.league.lobby')}</Link>
      </section>
    )
  }
  const { data } = state
  const open = now.getTime() < new Date(data.week.lock_at).getTime()
  const humans = data.league.league_members.filter((m) => !m.is_drone)

  return (
    <section className="page briefing">
      <LeagueNav leagueId={id} />
      <h1>{t('briefing.title', { n: data.week.number })}</h1>
      {data.week.is_final && <p className="final-banner">{t('briefing.final')}</p>}
      {open ? (
        <Countdown to={data.week.lock_at} label={t('briefing.lockIn')} />
      ) : (
        <p className="notice">{t('briefing.closed')}</p>
      )}
      <nav className="jump-nav" aria-label={t('briefing.sections')}>
        {(['squad', 'orders', 'pacts'] as const).map((section) => (
          <button
            key={section}
            type="button"
            className="button button-link"
            onClick={() => {
              document.getElementById(`${section}-h`)?.scrollIntoView({ behavior: 'smooth' })
            }}
          >
            {t(`briefing.jump.${section}`)}
          </button>
        ))}
      </nav>
      <SquadBuilder
        key={`${data.week.week}-${data.saved.submittedAt ?? ''}`}
        data={data}
        config={config}
        open={open}
        onSaved={refresh}
      />
      <OrdersPanel
        config={config}
        leagueId={id}
        members={humans}
        ammo={data.ammo}
        costs={data.costs}
        orders={data.orders}
        intel={data.intel}
        onPlayed={refresh}
      />
      <PactsPanel
        leagueId={id}
        me={data.me}
        members={humans}
        pacts={data.pacts}
        open={open}
        onChange={refresh}
      />
    </section>
  )
}
