import type { MessageKey } from '../i18n/en'

// Long-form rules summary, one file per language (rules.en.ts is the reference).
// {placeholders} are game_config values (engine/config.py), filled by the rules page:
// numeric keys by name, slot multipliers as {slot_<slot>}.
export interface RulesSection {
  id: string
  title: string
  paragraphs: string[]
}

export interface GlossaryEntry {
  term: MessageKey
  text: string
}

export interface RulesContent {
  intro: string
  sections: RulesSection[]
  glossary: GlossaryEntry[]
}
