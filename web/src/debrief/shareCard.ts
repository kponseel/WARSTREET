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
const MEDALS = ['#c9a227', '#9aa4b1', '#b06a35']
// The app's "tactical HUD" palette (styles/tokens.css).
const INK = '#1c2318'
const PAPER = '#eef0e4'
const MUTED = '#c8ceb8'
const SIGNAL = '#c2410c'
const GRID = 'rgba(238,240,228,0.06)'
const DISPLAY = '"Saira Stencil One", "Arial Black", system-ui, sans-serif'
const HUD = '"Chakra Petch", system-ui, sans-serif'

/** A panel with its top-left and bottom-right corners cut, like the app's cards. */
function bevelPath(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, cut: number): void {
  ctx.beginPath()
  ctx.moveTo(x + cut, y)
  ctx.lineTo(x + w, y)
  ctx.lineTo(x + w, y + h - cut)
  ctx.lineTo(x + w - cut, y + h)
  ctx.lineTo(x, y + h)
  ctx.lineTo(x, y + cut)
  ctx.closePath()
}

/** The bundled fonts, so the canvas does not fall back to a system font on first use. */
export async function loadCardFonts(): Promise<void> {
  try {
    await Promise.all([document.fonts.load(`84px ${DISPLAY}`), document.fonts.load(`700 56px ${HUD}`)])
  } catch {
    // Without the fonts the card is still drawn, with the fallbacks.
  }
}

export function drawShareCard(canvas: HTMLCanvasElement, text: CardText): void {
  canvas.width = SIZE
  canvas.height = SIZE
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.fillStyle = INK
  ctx.fillRect(0, 0, SIZE, SIZE)
  ctx.strokeStyle = GRID
  ctx.lineWidth = 2
  for (let v = 0; v <= SIZE; v += 54) {
    ctx.beginPath()
    ctx.moveTo(v, 0)
    ctx.lineTo(v, SIZE)
    ctx.moveTo(0, v)
    ctx.lineTo(SIZE, v)
    ctx.stroke()
  }
  ctx.fillStyle = SIGNAL
  ctx.fillRect(0, 0, SIZE, 14)
  ctx.fillRect(0, SIZE - 14, SIZE, 14)
  ctx.fillStyle = PAPER
  ctx.textAlign = 'center'
  ctx.font = `84px ${DISPLAY}`
  ctx.fillText(text.game, SIZE / 2, 150)
  ctx.font = `700 52px ${HUD}`
  ctx.fillText(text.title.toUpperCase(), SIZE / 2, 240)
  ctx.font = `400 36px ${HUD}`
  ctx.fillStyle = MUTED
  ctx.fillText(text.subtitle, SIZE / 2, 300)
  text.entries.slice(0, 3).forEach((entry, i) => {
    const y = 420 + i * 200
    bevelPath(ctx, 90, y - 70, SIZE - 180, 160, 28)
    ctx.fillStyle = 'rgba(238,240,228,0.08)'
    ctx.fill()
    ctx.strokeStyle = i === 0 ? SIGNAL : 'rgba(238,240,228,0.35)'
    ctx.lineWidth = 3
    ctx.stroke()
    ctx.fillStyle = MEDALS[i] ?? PAPER
    bevelPath(ctx, 140, y - 45, 100, 110, 18)
    ctx.fill()
    ctx.fillStyle = INK
    ctx.font = `700 60px ${HUD}`
    ctx.fillText(String(entry.rank), 190, y + 30)
    ctx.textAlign = 'left'
    ctx.fillStyle = PAPER
    ctx.font = `700 56px ${HUD}`
    ctx.fillText(entry.pseudo, 290, y + 5)
    ctx.font = `400 36px ${HUD}`
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
