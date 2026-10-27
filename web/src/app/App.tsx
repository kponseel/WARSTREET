import type { SupabaseClient } from '@supabase/supabase-js'
import { HashRouter, Route, Routes } from 'react-router'
import { AuthProvider } from '../auth/AuthProvider'
import { PendingRedirect } from '../auth/PendingRedirect'
import { RequireAuth } from '../auth/RequireAuth'
import { Header } from '../components/Header'
import { getSupabase } from '../lib/supabase'
import { Home } from '../pages/Home'
import { Join } from '../pages/Join'
import { Lobby } from '../pages/Lobby'
import { Login } from '../pages/Login'
import { NotFound } from '../pages/NotFound'
import { Rules } from '../pages/Rules'

// HashRouter: GitHub Pages has no SPA fallback.
export function App({ client = getSupabase() }: { client?: SupabaseClient | null }) {
  return (
    <AuthProvider client={client}>
      <HashRouter>
        <PendingRedirect />
        <Header />
        <main id="main">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/rules" element={<Rules />} />
            <Route
              path="/join/:code"
              element={
                <RequireAuth>
                  <Join />
                </RequireAuth>
              }
            />
            <Route
              path="/l/:id/lobby"
              element={
                <RequireAuth>
                  <Lobby />
                </RequireAuth>
              }
            />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </HashRouter>
    </AuthProvider>
  )
}
