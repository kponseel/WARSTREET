import type { SupabaseClient } from '@supabase/supabase-js'
import { useEffect, useState } from 'react'

// The rule values (engine/config.py mirrored to the game_config table). The UI only
// displays them; the RPCs enforce them (CLAUDE.md hard rule 6).
export class GameConfig {
  private readonly values: ReadonlyMap<string, unknown>

  constructor(rows: readonly { key: string; value: unknown }[]) {
    this.values = new Map(rows.map((r) => [r.key, r.value]))
  }

  /** From the build-time copy (content/gameConfig.generated.ts), for public pages. */
  static fromValues(values: Readonly<Record<string, unknown>>): GameConfig {
    return new GameConfig(Object.entries(values).map(([key, value]) => ({ key, value })))
  }

  /** Every numeric value by key, and slot multipliers as `slot_<slot>` (text placeholders). */
  numbers(): Record<string, number> {
    const result: Record<string, number> = {}
    for (const [key, value] of this.values) {
      if (typeof value === 'number') result[key] = value
    }
    const slots = this.values.get('slot_multipliers')
    if (typeof slots === 'object' && slots !== null) {
      for (const [slot, value] of Object.entries(slots)) {
        if (typeof value === 'number') result[`slot_${slot}`] = value
      }
    }
    return result
  }

  num(key: string): number {
    const value = this.values.get(key)
    if (typeof value !== 'number') throw new Error(`game_config.${key} is not a number`)
    return value
  }

  strings(key: string): string[] {
    const value = this.values.get(key)
    if (!Array.isArray(value) || !value.every((v) => typeof v === 'string')) {
      throw new Error(`game_config.${key} is not a list of strings`)
    }
    return value
  }

  numIn(key: string, field: string): number {
    const value = this.values.get(key)
    const inner: unknown =
      typeof value === 'object' && value !== null ? (value as Record<string, unknown>)[field] : null
    if (typeof inner !== 'number') throw new Error(`game_config.${key}.${field} is not a number`)
    return inner
  }
}

let cached: Promise<GameConfig> | null = null

export function loadGameConfig(client: SupabaseClient): Promise<GameConfig> {
  cached ??= (async () => {
    const { data, error } = await client.from('game_config').select('key, value')
    if (error) throw new Error(error.message)
    return new GameConfig(data)
  })().catch((error: unknown) => {
    cached = null
    throw error
  })
  return cached
}

export function resetGameConfigCache(): void {
  cached = null
}

export function useGameConfig(client: SupabaseClient | null): GameConfig | null {
  const [config, setConfig] = useState<GameConfig | null>(null)
  useEffect(() => {
    if (!client) return
    let active = true
    void loadGameConfig(client).then(
      (loaded) => {
        if (active) setConfig(loaded)
      },
      () => undefined,
    )
    return () => {
      active = false
    }
  }, [client])
  return config
}
