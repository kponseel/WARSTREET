import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { devAdvance, devClearClock, devLeague } from './dev'
import { logIn } from './session'

const email = `front-${Date.now().toString(36)}@example.test`

test.afterAll(() => {
  devClearClock()
})

test('a week unfolds: live front, resupply swap and order, Thursday dispatch', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 })
  await page.goto('/#/login')
  await logIn(page, email)
  await expect(page.getByRole('heading', { name: 'My leagues' })).toBeVisible()
  const league = devLeague([email], 3, false)

  // Monday, after the EU open: live scores, the phase banner, the Monday Dispatch.
  devAdvance(league.league_id, 'monday', false)
  await page.goto(`/#/l/${league.league_id}/front`)
  await expect(page.getByRole('heading', { name: 'The front — week 1' })).toBeVisible()
  await expect(page.getByText('European Assault')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Live leaderboard' })).toBeVisible()
  await expect(page.getByText(/My live score: -?\d+ ₩/)).toBeVisible()
  await expect(page.locator('.feed-dispatch')).toHaveCount(1)
  const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(axe.violations.map((v) => v.id)).toEqual([])

  // Wednesday night: resupply opens; one valid swap, cancelled, then made again.
  devAdvance(league.league_id, 'resupply', false)
  await page.goto(`/#/l/${league.league_id}/resupply`)
  await expect(page.getByRole('heading', { name: 'Resupply — week 1' })).toBeVisible()
  await expect(page.getByText('Swaps used: 0/1.')).toBeVisible()
  const swapValid = async () => {
    for (const button of await page.getByRole('button', { name: 'Swap', exact: true }).all()) {
      await button.click()
      const valid = page.locator('button:enabled', { hasText: /^[A-Z0-9.]+$/ }).filter({
        has: page.locator('xpath=self::*[starts-with(@aria-label, "Swap with")]'),
      })
      if ((await valid.count()) > 0) {
        await valid.first().click()
        return
      }
      await page.getByRole('button', { name: 'Cancel' }).click()
    }
    throw new Error('no valid swap')
  }
  await swapValid()
  await expect(page.getByText('Swaps used: 1/1.')).toBeVisible()
  await page.getByRole('button', { name: 'Cancel the swap' }).click()
  await expect(page.getByText('Swaps used: 0/1.')).toBeVisible()
  await swapValid()
  await expect(page.getByText('Swaps used: 1/1.')).toBeVisible()

  const strike = page.locator('.order', { hasText: 'Orbital Strike' })
  await strike.getByRole('button', { name: 'Prepare' }).click()
  await strike.getByRole('button', { name: /Review/ }).click()
  await strike.getByRole('button', { name: 'Play the order' }).click()
  await expect(page.getByText(/Orbital Strike → .* · 2 credit\(s\) · waiting/)).toBeVisible()

  // Thursday: the swap applies (the incoming unit plays Segment 2 only), the Dispatch.
  devAdvance(league.league_id, 'thursday', false)
  await page.goto(`/#/l/${league.league_id}/front`)
  await expect(page.getByText('Segment 2 only')).toBeVisible()
  await expect(page.getByText('Segment 1 only')).toBeVisible()
  await expect(page.locator('.feed-dispatch')).toHaveCount(2)
  await expect(page.getByText(/played Orbital Strike on/)).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBe(0)
})
