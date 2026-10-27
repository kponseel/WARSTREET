// Drives the dev mode (python -m jobs.dev) from the end-to-end tests: leagues of bots on
// the local Supabase, and a simulated clock moved phase by phase.
import { execFileSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const VENV_PYTHON = join(ROOT, '.venv', 'bin', 'python')
const PYTHON = process.env.WARSTREET_PYTHON ?? (existsSync(VENV_PYTHON) ? VENV_PYTHON : 'python3')

function dev(args: string[]): unknown {
  const out = execFileSync(PYTHON, ['-m', 'jobs.dev', '--json', ...args], {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'inherit'],
    timeout: 240_000,
  })
  const last = out.trim().split('\n').at(-1) ?? '{}'
  return JSON.parse(last) as unknown
}

export interface DevLeague {
  league_id: string
  invite_code: string
  week: string
  clock: string
}

/** A started league (synthetic prices) with `bots` bots and the given local accounts. */
export function devLeague(me: string[], bots = 3): DevLeague {
  return dev([
    'league',
    '--bots',
    String(bots),
    '--prices',
    'synthetic',
    ...me.flatMap((email) => ['--me', email]),
  ]) as DevLeague
}

/** Moves the simulated clock (lock, monday, resupply, thursday, debrief, next, end…). */
export function devAdvance(leagueId: string, to: string): { clock: string } {
  return dev(['advance', '--league', leagueId, '--to', to, '--prices', 'synthetic']) as {
    clock: string
  }
}

export function devClearClock(): void {
  dev(['clock', '--clear'])
}
