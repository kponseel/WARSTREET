import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Browser, type Page } from '@playwright/test'
import { loginLink } from './mailbox'
import { logIn } from './session'

const run = Date.now().toString(36)
const email = (who: string) => `${who}-${run}@example.test`

async function newPlayer(browser: Browser): Promise<Page> {
  const context = await browser.newContext()
  return context.newPage()
}

async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  expect(results.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([])
}

async function fillMember(page: Page, pseudo: string, commander: string) {
  await page.getByLabel('Your pseudo in this league').fill(pseudo)
  await page.getByRole('radio', { name: new RegExp(commander) }).check()
}

test('create, join by code, everyone ready, the host starts the campaign', async ({ browser }) => {
  // Host: logs in from the home page and creates the league.
  const host = await newPlayer(browser)
  await host.goto('/#/login')
  await expectAccessible(host)
  await logIn(host, email('host'))
  await expect(host.getByRole('heading', { name: 'My leagues' })).toBeVisible()
  await host.getByLabel('League name').fill(`Smoke ${run}`)
  await fillMember(host, 'Alpha', 'The Bastion')
  await expectAccessible(host)
  await host.getByRole('button', { name: 'Create the league' }).click()
  await expect(host.getByRole('heading', { name: `Smoke ${run}` })).toBeVisible()
  const code = (await host.locator('.invite .code').textContent()) ?? ''
  expect(code).toMatch(/^[A-Z0-9]{6}$/)
  await expectAccessible(host)

  // Bravo opens the join link before logging in: the link survives the login round-trip.
  const bravo = await newPlayer(browser)
  await bravo.goto(`/#/join/${code}`)
  await logIn(bravo, email('bravo'))
  await expect(bravo.getByRole('heading', { name: 'Join a league' })).toBeVisible()
  await expect(bravo.getByText(`Smoke ${run}`)).toBeVisible()
  await fillMember(bravo, 'Bravo', 'The Shadow')
  await bravo.getByRole('button', { name: 'Join the league' }).click()
  await expect(bravo.getByRole('heading', { name: `Smoke ${run}` })).toBeVisible()

  // Charlie logs in with the magic link (PKCE ?code= exchanged before the router mounts),
  // then types the invite code on the home page.
  const charlie = await newPlayer(browser)
  await charlie.goto('/#/login')
  await charlie.getByLabel('Email').fill(email('charlie'))
  await charlie.getByRole('button', { name: 'Send me a login email' }).click()
  await expect(charlie.getByText(`Email sent to ${email('charlie')}`)).toBeVisible()
  await charlie.goto(await loginLink(email('charlie')))
  await expect(charlie.getByRole('heading', { name: 'My leagues' })).toBeVisible()
  expect(new URL(charlie.url()).search).toBe('')
  await charlie.getByLabel('Invite code').fill(code.toLowerCase())
  await charlie.getByRole('button', { name: 'Continue' }).click()
  await fillMember(charlie, 'Charlie', 'The Berserker')
  await charlie.getByRole('button', { name: 'Join the league' }).click()

  // Realtime: the host sees both newcomers without reloading.
  const members = host.getByRole('list', { name: 'Players' })
  await expect(members.getByText('Bravo')).toBeVisible()
  await expect(members.getByText('Charlie')).toBeVisible()

  const start = host.getByRole('button', { name: 'Start the campaign' })
  for (const page of [host, bravo, charlie]) {
    await expect(start).toBeDisabled()
    await page.getByRole('button', { name: 'I’m ready' }).click()
    await expect(page.getByRole('button', { name: /Ready ✓/ })).toBeVisible()
  }
  await expect(host.getByText('3 ready, 3 needed to start.')).toBeVisible()
  await expect(start).toBeEnabled()
  await start.click()

  // Everyone, the host included, sees the campaign start (Realtime on weeks).
  for (const page of [host, bravo, charlie]) {
    await expect(page.getByText(/The campaign has started/)).toBeVisible()
  }
  await expect(members.getByText('Random Drone')).toBeVisible()

  // The language choice is saved in the profile: a fresh English browser logs in in French.
  await bravo.getByRole('button', { name: 'FR' }).click()
  await expect(bravo.getByRole('heading', { name: 'Joueurs' })).toBeVisible()
  const elsewhere = await newPlayer(browser)
  await elsewhere.goto('/#/login')
  await logIn(elsewhere, email('bravo'))
  await expect(elsewhere.getByRole('heading', { name: 'Mes ligues' })).toBeVisible()
})
