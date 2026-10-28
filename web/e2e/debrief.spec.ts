import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { devAdvance, devClearClock, devLeague } from './dev'
import { logIn } from './session'

const email = `debrief-${Date.now().toString(36)}@example.test`

test.afterAll(() => {
  devClearClock()
})

test('Friday night: ranking, breakdown, Drone verdict, share card, campaign', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 })
  await page.goto('/#/login')
  await logIn(page, email)
  await expect(page.getByRole('heading', { name: 'My leagues' })).toBeVisible()
  const league = devLeague([email], 3)
  devAdvance(league.league_id, 'debrief')

  await page.goto(`/#/l/${league.league_id}/debrief/latest`)
  await expect(page.getByRole('heading', { name: 'Debrief — week 1' })).toBeVisible()
  await expect(page.locator('.dispatch')).toContainText('₩')
  const rows = page.locator('.board .board-row')
  await expect(rows).toHaveCount(4) // 4 humans (the Drone is in its own verdict)
  await rows.first().locator('.board-line').click()
  await expect(page.getByRole('table')).toContainText('Stock picking')
  await expect(page.getByRole('table')).toContainText('Total')
  await expect(page.locator('.extremes')).toContainText(/Best unit: .+ Worst unit: /)
  await expect(page.getByRole('heading', { name: "The Drone's verdict" })).toBeVisible()
  await expect(page.locator('.board-row').first().locator('.badge-warlord')).toBeVisible()

  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Create the podium image' }).click()
  expect((await download).suggestedFilename()).toBe('podium-week-1.png')

  const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(axe.violations.map((v) => v.id)).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBe(0)

  // The campaign page and the badges next to pseudos the week after.
  await page.goto(`/#/l/${league.league_id}/campaign`)
  await expect(page.getByRole('heading', { name: 'Standings' })).toBeVisible()
  await expect(page.locator('.standings tbody tr')).toHaveCount(4)
  await expect(page.getByRole('img', { name: 'Cumulative campaign points per week' })).toBeVisible()
  await page.goto(`/#/l/${league.league_id}/lobby`)
  await expect(page.locator('.member-list .badge-warlord')).toBeVisible()
})
