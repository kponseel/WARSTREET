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

export function drawShareCard(canvas: HTMLCanvasElement, text: CardText): void {
  canvas.width = SIZE
  canvas.height = SIZE
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.fillStyle = '#1f3a5f'
  ctx.fillRect(0, 0, SIZE, SIZE)
  ctx.fillStyle = '#ffffff'
  ctx.textAlign = 'center'
  ctx.font = '900 84px "Arial Black", system-ui, sans-serif'
  ctx.fillText(text.game, SIZE / 2, 150)
  ctx.font = '700 52px system-ui, sans-serif'
  ctx.fillText(text.title, SIZE / 2, 240)
  ctx.font = '400 36px system-ui, sans-serif'
  ctx.fillStyle = '#d5dae1'
  ctx.fillText(text.subtitle, SIZE / 2, 300)
  text.entries.slice(0, 3).forEach((entry, i) => {
    const y = 420 + i * 200
    ctx.fillStyle = 'rgba(255,255,255,0.08)'
    ctx.fillRect(90, y - 70, SIZE - 180, 160)
    ctx.fillStyle = MEDALS[i] ?? '#ffffff'
    ctx.beginPath()
    ctx.arc(190, y + 10, 55, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = '#14181f'
    ctx.font = '900 56px system-ui, sans-serif'
    ctx.fillText(String(entry.rank), 190, y + 30)
    ctx.textAlign = 'left'
    ctx.fillStyle = '#ffffff'
    ctx.font = '800 56px system-ui, sans-serif'
    ctx.fillText(entry.pseudo, 290, y + 5)
    ctx.font = '400 36px system-ui, sans-serif'
    ctx.fillStyle = '#d5dae1'
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
