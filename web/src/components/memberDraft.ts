import type { GameConfig } from '../data/gameConfig'

export interface MemberDraft {
  pseudo: string
  commander: string | null
  color: string | null
}

export function emptyDraft(config: GameConfig | null): MemberDraft {
  return { pseudo: '', commander: null, color: config?.strings('avatar_colors')[0] ?? null }
}
