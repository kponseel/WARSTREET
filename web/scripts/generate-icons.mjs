// Regenerates public/icon-192.png and public/icon-512.png from public/icon.svg.
// Run with: node scripts/generate-icons.mjs (needs Playwright with Chromium installed).
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const publicDir = fileURLToPath(new URL('../public/', import.meta.url))
const svg = await readFile(`${publicDir}icon.svg`, 'utf8')
const browser = await chromium.launch()
for (const size of [192, 512]) {
  const page = await browser.newPage({ viewport: { width: size, height: size } })
  await page.setContent(
    `<style>html,body{margin:0}svg{display:block;width:${size}px;height:${size}px}</style>${svg}`,
  )
  await page.screenshot({ path: `${publicDir}icon-${size}.png`, omitBackground: true })
  await page.close()
}
await browser.close()
console.log('icons written')
