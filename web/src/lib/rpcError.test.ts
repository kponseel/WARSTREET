import { describe, expect, it } from 'vitest'
import { translate } from '../i18n/translate'
import { rpcErrorMessage } from './rpcError'

describe('rpcErrorMessage', () => {
  it('maps a known code and its variables', () => {
    const { key, vars } = rpcErrorMessage({
      message: 'NOT_ENOUGH_AMMO',
      details: '{"cost": 3, "balance": 1}',
    })
    expect(key).toBe('error.NOT_ENOUGH_AMMO')
    expect(translate('en', key, vars)).toBe('Not enough credits: this order costs 3, you have 1.')
    expect(translate('fr', key, vars)).toBe(
      'Pas assez de crédits : cet ordre coûte 3, vous avez 1.',
    )
  })

  it('falls back for unknown codes and unreadable details', () => {
    expect(rpcErrorMessage({ message: 'SOMETHING_ELSE' }).key).toBe('error.unknown')
    expect(rpcErrorMessage({ message: 'LEAGUE_FULL', details: 'oops' })).toEqual({
      key: 'error.LEAGUE_FULL',
      vars: {},
    })
  })
})
