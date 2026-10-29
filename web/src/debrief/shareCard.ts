// The weekly podium as an image for the group chat (drawn in the browser, no server).
export interface PodiumEntry {
  rank: number
  pseudo: string
  color: string
  pf: string
  points: string
}

export interface CardText {
  game: string
  title: string
  subtitle: string
  entries: PodiumEntry[]
}

const SIZE = 1080
const MEDALS = ['#c9a227', '#8a96a6', '#b06a35']
// The app's "white armour" palette (styles/tokens.css).
const NAVY = '#0d1b2a'
const WHITE = '#ffffff'
const PAPER = '#eef2f6'
const MUTED = '#44546a'
const BLUE = '#0050c8'
const DOT = '#c6d1dd'
const DISPLAY = 'Orbitron, "Arial Black", system-ui, sans-serif'
const HUD = 'Rajdhani, system-ui, sans-serif'

/** A hexagon centred on (cx, cy), like the app's rank plates. */
function hexPath(ctx: CanvasRenderingContext2D, cx: number, cy: number, w: number, h: number): void {
  ctx.beginPath()
  ctx.moveTo(cx - w / 4, cy - h / 2)
  ctx.lineTo(cx + w / 4, cy - h / 2)
  ctx.lineTo(cx + w / 2, cy)
  ctx.lineTo(cx + w / 4, cy + h / 2)
  ctx.lineTo(cx - w / 4, cy + h / 2)
  ctx.lineTo(cx - w / 2, cy)
  ctx.closePath()
}

/** The blue corner brackets of the app's panels (top-left and bottom-right). */
function brackets(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, size: number): void {
  ctx.fillStyle = BLUE
  ctx.fillRect(x, y, size, 4)
  ctx.fillRect(x, y, 4, size)
  ctx.fillRect(x + w - size, y + h - 4, size, 4)
  ctx.fillRect(x + w - 4, y + h - size, 4, size)
}

/** The bundled fonts, so the canvas does not fall back to a system font on first use. */
export async function loadCardFonts(): Promise<void> {
  try {
    await Promise.all([document.fonts.load(`700 84px ${DISPLAY}`), document.fonts.load(`700 56px ${HUD}`)])
  } catch {
    // Without the fonts the card is still drawn, with the fallbacks.
  }
}

export function drawShareCard(canvas: HTMLCanvasElement, text: CardText): void {
  canvas.width = SIZE
  canvas.height = SIZE
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.fillStyle = PAPER
  ctx.fillRect(0, 0, SIZE, SIZE)
  ctx.fillStyle = DOT
  for (let x = 27; x < SIZE; x += 54) {
    for (let y = 27; y < SIZE; y += 54) {
      ctx.beginPath()
      ctx.arc(x, y, 3, 0, Math.PI * 2)
      ctx.fill()
    }
  }
  ctx.fillStyle = BLUE
  ctx.fillRect(0, 0, SIZE, 10)
  ctx.fillRect(0, SIZE - 10, SIZE, 10)
  ctx.fillStyle = BLUE
  ctx.textAlign = 'center'
  ctx.font = `700 76px ${DISPLAY}`
  ctx.fillText(text.game, SIZE / 2, 150)
  ctx.fillStyle = NAVY
  ctx.font = `700 52px ${HUD}`
  ctx.fillText(text.title.toUpperCase(), SIZE / 2, 240)
  ctx.font = `600 36px ${HUD}`
  ctx.fillStyle = MUTED
  ctx.fillText(text.subtitle, SIZE / 2, 300)
  text.entries.slice(0, 3).forEach((entry, i) => {
    const y = 420 + i * 200
    ctx.fillStyle = WHITE
    ctx.fillRect(90, y - 70, SIZE - 180, 160)
    ctx.strokeStyle = i === 0 ? BLUE : DOT
    ctx.lineWidth = i === 0 ? 4 : 2
    ctx.strokeRect(90, y - 70, SIZE - 180, 160)
    brackets(ctx, 90, y - 70, SIZE - 180, 160, 36)
    ctx.fillStyle = MEDALS[i] ?? BLUE
    hexPath(ctx, 190, y + 10, 120, 104)
    ctx.fill()
    ctx.fillStyle = NAVY
    ctx.font = `700 60px ${HUD}`
    ctx.fillText(String(entry.rank), 190, y + 30)
    ctx.textAlign = 'left'
    ctx.fillStyle = NAVY
    ctx.font = `700 56px ${HUD}`
    ctx.fillText(entry.pseudo, 290, y + 5)
    ctx.font = `600 36px ${HUD}`
    ctx.fillStyle = MUTED
    ctx.fillText(`${entry.pf} · ${entry.points}`, 290, y + 60)
    ctx.textAlign = 'center'
  })
}

export async function shareOrDownload(canvas: HTMLCanvasElement, fileName: string): Promise<'shared' | 'downloaded'> {
  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob(resolve, 'image/png')
  })
  if (!blob) throw new Error('image generation failed')
  const file = new File([blob], fileName, { type: 'image/png' })
  if (typeof navigator.canShare === 'function' && navigator.canShare({ files: [file] })) {
    await navigator.share({ files: [file] })
    return 'shared'
  }
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()
  URL.revokeObjectURL(url)
  return 'downloaded'
}
