import { describe, expect, it } from 'vitest'
import { canStart, humans, inviteLink, readyCount, type League, type Member } from './leagues'

const member = (id: string, extra: Partial<Member> = {}): Member => ({
  member_id: id,
  user_id: `user-${id}`,
  pseudo: id,
  commander: 'bastion',
  avatar_color: '#1f3a5f',
  ready: false,
  is_drone: false,
  joined_at: '2026-11-01T10:00:00Z',
  ...extra,
})

const league = (members: Member[], status: League['status'] = 'lobby'): League => ({
  id: 'L',
  name: 'Test',
  status,
  invite_code: 'ABC234',
  host_id: 'user-a',
  max_players: 5,
  campaign_weeks: 8,
  drone_enabled: true,
  start_week: null,
  league_members: members,
})

describe('lobby rules', () => {
  const drone = member('drone', { user_id: null, is_drone: true, ready: true, commander: null })

  it('counts only ready humans (the Drone is always "ready")', () => {
    const l = league([member('a', { ready: true }), member('b'), drone])
    expect(humans(l)).toHaveLength(2)
    expect(readyCount(l)).toBe(1)
  })

  it('lets only the host start, in the lobby, with enough humans ready', () => {
    const ready = [member('a', { ready: true }), member('b', { ready: true }), member('c', { ready: true })]
    expect(canStart(league(ready), 'user-a', 3)).toBe(true)
    expect(canStart(league(ready), 'user-b', 3)).toBe(false)
    expect(canStart(league(ready, 'active'), 'user-a', 3)).toBe(false)
    expect(canStart(league([...ready.slice(0, 2), member('c')]), 'user-a', 3)).toBe(false)
  })

  it('builds the invite link on the app address', () => {
    expect(inviteLink({ origin: 'https://me.github.io', pathname: '/warstreet/' }, 'ABC234')).toBe(
      'https://me.github.io/warstreet/#/join/ABC234',
    )
  })
})
