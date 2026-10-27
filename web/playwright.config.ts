import { defineConfig, devices } from '@playwright/test'

// End-to-end smoke test against a local Supabase (`supabase start`): real Auth, RLS,
// RPCs and Realtime; login codes are read from the local mailbox (Mailpit).
// Build the app with the local VITE_SUPABASE_* values first (see README).
export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    locale: 'en-US',
    trace: 'retain-on-failure',
    ...devices['Pixel 7'],
  },
  webServer: {
    command: 'npm run preview -- --host 127.0.0.1 --port 4173 --strictPort',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: !process.env.CI,
  },
})
