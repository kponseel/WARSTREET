// Lighthouse mobile accessibility check of the public pages (prompts/05: score >= 95).
// Usage (after `npm run build`): node scripts/lighthouse-a11y.mjs
// Needs Chromium: CHROME_PATH, else the browser installed for Playwright.
import { execFileSync, spawn } from 'node:child_process'
import { mkdtempSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { chromium } from '@playwright/test'

const MIN_SCORE = 0.95
const PORT = 4174
const PAGES = ['#/', '#/login', '#/rules']
const base = `http://127.0.0.1:${PORT}/`
const chrome = process.env.CHROME_PATH ?? chromium.executablePath()

const server = spawn('npx', ['vite', 'preview', '--host', '127.0.0.1', '--port', String(PORT), '--strictPort'], {
  stdio: 'ignore',
})
try {
  for (let i = 0; i < 60; i += 1) {
    try {
      if ((await fetch(base)).ok) break
    } catch {
      // not up yet
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  const dir = mkdtempSync(join(tmpdir(), 'lighthouse-'))
  let failed = false
  for (const page of PAGES) {
    const out = join(dir, 'report.json')
    execFileSync(
      'npx',
      [
        '--yes',
        'lighthouse@13.5.0',
        `${base}${page}`,
        '--only-categories=accessibility',
        '--form-factor=mobile',
        '--chrome-flags=--headless=new --no-sandbox',
        '--output=json',
        `--output-path=${out}`,
        '--quiet',
      ],
      { stdio: 'inherit', env: { ...process.env, CHROME_PATH: chrome } },
    )
    const report = JSON.parse(readFileSync(out, 'utf8'))
    const score = report.categories.accessibility.score
    const failing = Object.values(report.audits)
      .filter((a) => a.score === 0 && a.scoreDisplayMode === 'binary')
      .map((a) => a.id)
    console.log(`${page}: accessibility ${Math.round(score * 100)}${failing.length ? ` (${failing.join(', ')})` : ''}`)
    if (score < MIN_SCORE) failed = true
  }
  if (failed) {
    console.error(`Accessibility below ${MIN_SCORE * 100} on at least one page`)
    process.exitCode = 1
  }
} finally {
  server.kill()
}
