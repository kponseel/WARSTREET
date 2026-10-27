import type { ReactNode } from 'react'

// Original geometric glyphs for the 7 commanders (CLAUDE.md hard rule 7: nothing borrowed).
const GLYPHS: Record<string, ReactNode> = {
  bastion: (
    <>
      <path d="M12 2.5 19.5 5.5V11c0 4.6-3.2 8.2-7.5 10.5C7.7 19.2 4.5 15.6 4.5 11V5.5Z" />
      <path d="M8 9.5h8M8 13.5h8" />
    </>
  ),
  berserker: (
    <>
      <path d="M4 13 12 5l8 8" />
      <path d="M4 20l8-8 8 8" />
    </>
  ),
  prophet: (
    <>
      <path d="M3.5 5h17L12 20.5Z" />
      <circle cx="12" cy="10" r="1.6" fill="currentColor" />
    </>
  ),
  hunter: (
    <>
      <circle cx="12" cy="12" r="7" />
      <path d="M12 2v5M12 17v5M2 12h5M17 12h5" />
      <circle cx="12" cy="12" r="1.2" fill="currentColor" />
    </>
  ),
  shadow: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 3a9 9 0 0 0 0 18 5.5 9 0 0 1 0-18Z" fill="currentColor" />
    </>
  ),
  technomancer: (
    <>
      <rect x="7" y="7" width="10" height="10" rx="1.5" />
      <path d="M10 7V3.5M14 7V3.5M10 20.5V17M14 20.5V17M7 10H3.5M7 14H3.5M20.5 10H17M20.5 14H17" />
      <circle cx="12" cy="12" r="1.6" fill="currentColor" />
    </>
  ),
  quartermaster: (
    <>
      <rect x="4" y="7" width="16" height="13" rx="1" />
      <path d="M4 11h16M12 11v9M9 4h6l2 3H7Z" />
    </>
  ),
}

export function CommanderEmblem({ code, size = 32 }: { code: string; size?: number }) {
  return (
    <svg
      className="emblem"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {GLYPHS[code] ?? <circle cx="12" cy="12" r="8" />}
    </svg>
  )
}
