import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { logIn } from './session'

const email = `tutorial-${Date.now().toString(36)}@example.test`

async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(results.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([])
}

test('first launch shows the tutorial once; Help opens it again', async ({ page }) => {
  await page.goto('/#/login')
  await logIn(page, email, { tutorial: true })
  const title = page.getByRole('heading', { level: 1 })
  await expect(title).toHaveText('Welcome to WARSTREET')
  await expect(page.getByText('Step 1 of 7')).toBeVisible()
  await expectAccessible(page)

  await page.getByRole('button', { name: 'Next' }).click()
  await expect(title).toHaveText('War Points (₩)')
  await expect(page.getByText(/^Units: \+\d+ ₩$/)).toBeVisible()
  for (let i = 0; i < 5; i += 1) await page.getByRole('button', { name: 'Next' }).click()
  await expect(title).toHaveText('Commanders')
  await page.getByText('See an example').first().click()
  await expect(page.getByText(/₩ becomes/).first()).toBeVisible()
  await expectAccessible(page)

  // "Don't show again" is ticked by default: finishing hides it for good on this device.
  await expect(page.getByRole('checkbox', { name: /Don’t show this automatically again/ })).toBeChecked()
  await page.getByRole('button', { name: 'Start playing' }).click()
  await expect(page.getByRole('heading', { name: 'My leagues' })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'My leagues' })).toBeVisible()

  // Help (left of Rules) opens it again, then comes back; Log out is at the bottom now.
  await page.getByRole('link', { name: 'Help' }).click()
  await expect(title).toHaveText('Welcome to WARSTREET')
  await expect(page.getByRole('checkbox')).toHaveCount(0)
  await page.getByRole('button', { name: 'Skip the tutorial' }).click()
  await expect(page.getByRole('heading', { name: 'My leagues' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible()
})
