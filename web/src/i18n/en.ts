// Reference language. Every key must also exist in fr.ts (enforced by the type and a test).
// Variables use {name} placeholders.
export const en = {
  'app.tagline': 'Weekly fantasy stock-market war game for friends.',
  'header.language': 'Language',
  'language.en': 'English',
  'language.fr': 'Français',
  'home.title': 'Welcome to {game}',
  'home.intro':
    'Draft 5 real EU and US stocks every weekend, attack your rivals with orders mid-week and climb the leaderboard every Friday night.',
  'home.comingSoon': 'The front is being built. Leagues open soon.',
  'home.backend.ok': 'Server connection configured.',
  'home.backend.missing': 'Server connection not configured yet.',
  'notFound.title': 'Page not found',
  'notFound.back': 'Back to home',
} as const satisfies Record<string, string>

export type MessageKey = keyof typeof en
