import { useState, type ReactNode } from 'react'
import { useLocation } from 'react-router'
import { useAuth } from '../auth/context'
import { Tutorial } from './Tutorial'
import { isTutorialDismissed, wasTutorialSeenThisVisit } from './tutorialState'

// Pages that never wait behind the tutorial (it is reachable from Help anyway).
const EXEMPT = new Set(['/tutorial', '/rules', '/login', '/status', '/debug'])

/**
 * First launch: a logged-in player sees the tutorial before the page they opened (an
 * invite link included: that page shows right after). Once per visit, until dismissed.
 */
export function TutorialGate({ children }: { children: ReactNode }) {
  const { session } = useAuth()
  const { pathname } = useLocation()
  const [done, setDone] = useState(false)
  // Read at every render: the player may log in (or dismiss it elsewhere) after this mounted.
  const show = !done && !isTutorialDismissed() && !wasTutorialSeenThisVisit()
  if (session && show && !EXEMPT.has(pathname)) {
    return (
      <Tutorial
        auto
        onDone={() => {
          setDone(true)
        }}
      />
    )
  }
  return children
}
