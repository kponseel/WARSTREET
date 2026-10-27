import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { devAdvance, devClearClock, devLeague } from './dev'
import { logIn } from './session'

const email = `briefing-${Date.now().toString(36)}@example.test`

test.afterAll(() => {
  devClearClock()
})

test('briefing: build a squad, see why it is invalid, play orders, answer a pact', async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 740 })
  // The account must exist before the dev tool adds it to a league of bots.
  await page.goto('/#/login')
  await logIn(page, email)
  await expect(page.getByRole('heading', { name: 'My leagues' })).toBeVisible()
  const league = devLeague([email], 3, false)

  await page.goto(`/#/l/${league.league_id}/briefing`)
  await expect(page.getByRole('heading', { name: 'Briefing — week 1' })).toBeVisible()
  await expect(page.getByText('Dev mode: simulated clock')).toBeVisible()
  await expect(page.getByText('Lock in')).toBeVisible()

  // Two US units as Champion and Veteran: the rule is shown before saving.
  await page.getByRole('button', { name: /^Champion/ }).click()
  await page.getByLabel('Region').selectOption('US')
  await page.locator('button:enabled', { hasText: 'Deploy' }).first().click()
  await page.getByRole('button', { name: /^Veteran/ }).click()
  await page.locator('button:enabled', { hasText: 'Deploy' }).first().click()
  await expect(
    page.getByText('Your Veteran must come from a different region than your Champion.'),
  ).toBeVisible()
  await expect(page.getByRole('button', { name: 'Save my squad' })).toBeDisabled()

  await page.getByRole('button', { name: 'Drone, suggest a squad' }).click()
  await expect(page.getByText('Valid squad.')).toBeVisible()
  await page.getByRole('button', { name: 'Save my squad' }).click()
  await expect(page.getByText('Saved. You can change it until the lock.')).toBeVisible()

  // Orders: confirmation step, then listed with their status.
  const field = page.locator('.order', { hasText: 'Force Field' })
  await field.getByRole('button', { name: 'Prepare' }).click()
  await field.getByRole('button', { name: /Review/ }).click()
  await field.getByRole('button', { name: 'Play the order' }).click()
  await expect(page.getByText(/Force Field · 1 ammo · waiting/)).toBeVisible()
  const intel = page.locator('.order', { hasText: 'Intel' })
  await intel.getByRole('button', { name: 'Prepare' }).click()
  await intel.getByRole('button', { name: /Review/ }).click()
  await intel.getByRole('button', { name: 'Play the order' }).click()
  await expect(page.getByRole('heading', { name: /Intel on/ })).toBeVisible()
  await expect(page.getByText(/they may have changed it since/)).toBeVisible()

  // Pacts: propose one to a bot.
  await page.getByRole('button', { name: /Propose a pact to/ }).first().click()
  await expect(page.getByText(/Waiting for .* to answer/)).toBeVisible()

  const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(axe.violations.map((v) => v.id)).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBe(0)

  // Sunday 23:59 passes: squads are locked.
  devAdvance(league.league_id, 'lock', false)
  await page.reload()
  await expect(page.getByText('The briefing is closed: squads are locked.')).toBeVisible()
})
