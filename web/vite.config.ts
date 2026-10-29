import { execSync } from 'node:child_process'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import { defineConfig, type Plugin } from 'vitest/config'
import { GAME_NAME } from './src/config'

// GitHub Pages serves the app under /<repo-name>/; the deploy workflow sets BASE_PATH.
const base = process.env.BASE_PATH ?? '/'

// Injects GAME_NAME into index.html so the name lives only in src/config.ts.
const gameNameInHtml: Plugin = {
  name: 'game-name-in-html',
  transformIndexHtml: (html) => html.replaceAll('%GAME_NAME%', GAME_NAME),
}

// Build stamp shown at the bottom of every page, so a player can check which version
// they run (the PWA may still serve an old cache): the commit and the build time.
function commitSha(): string {
  const fromCi = process.env.GITHUB_SHA
  if (fromCi) return fromCi.slice(0, 7)
  try {
    return execSync('git rev-parse --short=7 HEAD', { encoding: 'utf8' }).trim()
  } catch {
    return 'dev'
  }
}

export default defineConfig({
  base,
  define: {
    __BUILD_SHA__: JSON.stringify(commitSha()),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
  plugins: [
    react(),
    gameNameInHtml,
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icon.svg'],
      // Fonts are precached too: the app looks the same offline.
      workbox: { globPatterns: ['**/*.{js,css,html,svg,png,woff2}'] },
      manifest: {
        name: GAME_NAME,
        short_name: GAME_NAME,
        description: 'Weekly fantasy stock-market war game for friends.',
        lang: 'en',
        display: 'standalone',
        start_url: '.',
        scope: '.',
        background_color: '#eef2f6',
        theme_color: '#ffffff',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
    }),
  ],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
  },
})
