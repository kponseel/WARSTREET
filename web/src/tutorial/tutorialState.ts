// "Don't show the tutorial again" lives on this device (owner's choice: no database change).
// Shown once per visit at most, so finishing it never brings it back until the next launch.
const DISMISSED_KEY = 'tutorial.dismissed'
const SEEN_KEY = 'tutorial.seen'

export function isTutorialDismissed(): boolean {
  try {
    return window.localStorage.getItem(DISMISSED_KEY) === '1'
  } catch {
    return false
  }
}

export function dismissTutorial(): void {
  try {
    window.localStorage.setItem(DISMISSED_KEY, '1')
  } catch {
    // Storage unavailable (private mode): the tutorial shows again next launch.
  }
}

export function wasTutorialSeenThisVisit(): boolean {
  try {
    return window.sessionStorage.getItem(SEEN_KEY) === '1'
  } catch {
    return false
  }
}

export function markTutorialSeen(): void {
  try {
    window.sessionStorage.setItem(SEEN_KEY, '1')
  } catch {
    // Storage unavailable: the gate's own state still hides it for this visit.
  }
}
