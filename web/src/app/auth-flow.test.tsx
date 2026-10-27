import type { SupabaseClient } from '@supabase/supabase-js'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { peekPendingPath } from '../lib/auth'
import { App } from './App'

function fakeClient() {
  const signInWithOtp = vi.fn().mockResolvedValue({ error: null })
  const verifyOtp = vi.fn().mockResolvedValue({ error: { code: 'otp_expired', message: 'x' } })
  const client = {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
      onAuthStateChange: vi.fn().mockReturnValue({ data: { subscription: { unsubscribe: vi.fn() } } }),
      signInWithOtp,
      verifyOtp,
      signOut: vi.fn(),
    },
  } as unknown as SupabaseClient
  return { client, signInWithOtp, verifyOtp }
}

describe('login flow (no network)', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.location.hash = ''
  })

  it('sends a logged-out join link to the login page and remembers it', async () => {
    window.location.hash = '#/join/ABC234'
    const { client } = fakeClient()
    render(
      <I18nProvider locale="en">
        <App client={client} />
      </I18nProvider>,
    )
    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(window.location.hash).toBe('#/login')
    expect(peekPendingPath()).toBe('/join/ABC234')
  })

  it('asks for the 6-digit code after sending the email, with the browser language', async () => {
    window.location.hash = '#/login'
    const { client, signInWithOtp, verifyOtp } = fakeClient()
    render(
      <I18nProvider locale="fr">
        <App client={client} />
      </I18nProvider>,
    )
    fireEvent.change(await screen.findByLabelText('E-mail'), { target: { value: 'a@b.test' } })
    fireEvent.click(screen.getByRole('button', { name: 'M’envoyer un e-mail de connexion' }))
    const codeInput = await screen.findByLabelText('Code à 6 chiffres')
    expect(signInWithOtp).toHaveBeenCalledWith(
      expect.objectContaining({
        email: 'a@b.test',
        options: expect.objectContaining({ data: { locale: 'fr' }, shouldCreateUser: true }) as unknown,
      }),
    )
    fireEvent.change(codeInput, { target: { value: '12a34' } })
    fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Tapez le code reçu')
    fireEvent.change(codeInput, { target: { value: '123456' } })
    fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }))
    await waitFor(() => {
      expect(verifyOtp).toHaveBeenCalledWith({ email: 'a@b.test', token: '123456', type: 'email' })
    })
    expect(await screen.findByRole('alert')).toHaveTextContent('Ce code est faux ou a expiré.')
  })
})
