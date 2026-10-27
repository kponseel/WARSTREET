import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './app/App'
import { I18nProvider } from './i18n/I18nProvider'
import { completeLoginFromUrl } from './lib/auth'
import { getSupabase } from './lib/supabase'
import './styles/tokens.css'
import './styles/global.css'

const root = document.getElementById('root')
if (!root) throw new Error('Missing #root element')

// The magic link comes back as ?code=… (PKCE): exchange it before the router mounts.
void completeLoginFromUrl(getSupabase()).finally(() => {
  createRoot(root).render(
    <StrictMode>
      <I18nProvider>
        <App />
      </I18nProvider>
    </StrictMode>,
  )
})
