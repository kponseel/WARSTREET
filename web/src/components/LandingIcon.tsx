// Simple original glyphs for the three landing steps (decorative: hidden from screen readers).
const PATHS: Record<'draft' | 'attack' | 'win', string> = {
  // Five units in formation.
  draft: 'M4 6h6v6H4zM14 6h6v6h-6zM24 6h6v6h-6zM9 18h6v6H9zM19 18h6v6h-6z',
  // A targeting reticle.
  attack: 'M17 3v6M17 25v6M3 17h6M25 17h6M17 10a7 7 0 1 0 0 14a7 7 0 1 0 0-14zM17 15a2 2 0 1 0 0 4a2 2 0 1 0 0-4z',
  // A chevron rank plate.
  win: 'M5 22l12-8 12 8M5 14l12-8 12 8M8 28h18',
}

export function LandingIcon({ kind }: { kind: keyof typeof PATHS }) {
  const filled = kind === 'draft'
  return (
    <svg className="landing-icon" viewBox="0 0 34 34" width={40} height={40} aria-hidden="true" focusable="false">
      <path
        d={PATHS[kind]}
        fill={filled ? 'currentColor' : 'none'}
        stroke={filled ? 'none' : 'currentColor'}
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
