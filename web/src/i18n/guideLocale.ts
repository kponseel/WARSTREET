import { detectLocale, isLocale, type Locale } from './translate'

// The guides (Help = tutorial, and Rules) have their own language, even while the rest of the
// app is English-only (owner's request): the phone's language at first, then the EN/FR choice
// made at their top, remembered on the device and shared by both guides.
const GUIDE_LOCALE_KEY = 'guide.locale'

export function readGuideLocale(): Locale {
  try {
    const stored = window.localStorage.getItem(GUIDE_LOCALE_KEY)
    if (isLocale(stored)) return stored
  } catch {
    // Storage unavailable: fall back to the phone's language.
  }
  return detectLocale(navigator.languages)
}

export function saveGuideLocale(locale: Locale): void {
  try {
    window.localStorage.setItem(GUIDE_LOCALE_KEY, locale)
  } catch {
    // Storage unavailable: the choice lasts for this visit.
  }
}
