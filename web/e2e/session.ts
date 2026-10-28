import { expect, type Page } from '@playwright/test'
import { loginCode } from './mailbox'

/**
 * Logs in on the current page with the 6-digit code from the local mailbox. The first-launch
 * tutorial is dismissed beforehand unless `tutorial` is set (tutorial.spec.ts).
 */
export async function logIn(page: Page, address: string, { tutorial = false } = {}) {
  await expect(page.getByRole('heading', { name: 'Log in' })).toBeVisible()
  if (!tutorial) {
    await page.evaluate(() => {
      window.localStorage.setItem('tutorial.dismissed', '1')
    })
  }
  await page.getByLabel('Email').fill(address)
  await page.getByRole('button', { name: 'Send me a login email' }).click()
  await expect(page.getByText(`Email sent to ${address}`)).toBeVisible()
  await page.getByLabel('6-digit code').fill(await loginCode(address))
  await page.getByRole('button', { name: 'Log in', exact: true }).click()
}
