import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { devAdvance, devClearClock, devLeague } from './dev'
import { logIn } from './session'

// Milestone 09 i18n audit: every screen of a week at 360 px: nothing wider than the screen,
// no clipped label, no axe violation. French is ~20 % longer than English, so it is the one
// to check, but it is switched off during development (ENABLED_LOCALES in
// src/i18n/translate.ts): the pass runs in English until French comes back. Then switch to
// French after login again (FR button) and use the French texts below.
const email = `narrow-${Date.now().toString(36)}@example.test`
const TEXT = {
  home: 'My leagues',
  status: 'Server status',
  healthy: 'Everything is running',
  debrief: /Debrief — week/,
} // French: Mes ligues · État du serveur · Tout fonctionne · /Bilan — semaine/

test.afterAll(() => {
  devClearClock()
})

/** Elements whose text is wider than their box (cut or spilling out). */
async function clipped(page: Page): Promise<string[]> {
  return page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>('button, a, label, th, td, h1, h2, h3, dt, dd, .tab, .chip')]
      .filter((el) => el.offsetParent !== null && el.scrollWidth > el.clientWidth + 1)
      .filter((el) => !el.closest('.skip-link, .visually-hidden, .breakdown, .standings, .catalogue-table'))
      .map((el) => `${el.tagName.toLowerCase()}: ${el.textContent.trim().slice(0, 40)}`),
  )
}

async function fits(page: Page, name: string): Promise<void> {
  await expect(page.locator('main h1').first()).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth), name).toBe(0)
  expect(await clipped(page), name).toEqual([])
  const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(axe.violations.map((v) => `${name}: ${v.id}`)).toEqual([])
}

test('every screen of a week fits at 360 px', async ({ page }) => {
  test.setTimeout(240_000)
  await page.setViewportSize({ width: 360, height: 740 })
  await page.goto('/#/login')
  await logIn(page, email)
  await expect(page.getByRole('heading', { name: TEXT.home })).toBeVisible()
  await fits(page, 'home')

  const league = devLeague([email], 3)
  const id = league.league_id
  const screens: [string, string][] = [
    [`/#/l/${id}/lobby`, 'lobby'],
    [`/#/l/${id}/briefing`, 'briefing'],
    ['/#/rules', 'rules'],
    ['/#/status', 'status'],
  ]
  for (const [path, name] of screens) {
    await page.goto(path)
    await fits(page, name)
  }
  await expect(page.getByRole('heading', { name: TEXT.status })).toBeVisible()
  await expect(page.locator('.health-banner')).toContainText(TEXT.healthy)

  devAdvance(id, 'monday')
  await page.goto(`/#/l/${id}/front`)
  await fits(page, 'front')
  devAdvance(id, 'resupply')
  await page.goto(`/#/l/${id}/resupply`)
  await fits(page, 'resupply')
  devAdvance(id, 'debrief')
  await page.goto(`/#/l/${id}/debrief/latest`)
  await expect(page.getByRole('heading', { name: TEXT.debrief })).toBeVisible()
  await fits(page, 'debrief')
  await page.goto(`/#/l/${id}/campaign`)
  await fits(page, 'campaign')
})
