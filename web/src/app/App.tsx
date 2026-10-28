import type { SupabaseClient } from '@supabase/supabase-js'
import { HashRouter, Route, Routes } from 'react-router'
import { AuthProvider } from '../auth/AuthProvider'
import { PendingRedirect } from '../auth/PendingRedirect'
import { RequireAuth } from '../auth/RequireAuth'
import { BuildStamp } from '../components/BuildStamp'
import { DevBanner } from '../components/DevBanner'
import { Header } from '../components/Header'
import { ClockProvider } from '../data/ClockProvider'
import { getSupabase } from '../lib/supabase'
import { Briefing } from '../pages/Briefing'
import { Campaign } from '../pages/Campaign'
import { Debrief } from '../pages/Debrief'
import { Debug } from '../pages/Debug'
import { Front } from '../pages/Front'
import { Home } from '../pages/Home'
import { Join } from '../pages/Join'
import { Lobby } from '../pages/Lobby'
import { Login } from '../pages/Login'
import { NotFound } from '../pages/NotFound'
import { Resupply } from '../pages/Resupply'
import { Rules } from '../pages/Rules'
import { Status } from '../pages/Status'

const PRIVATE_ROUTES = [
  { path: '/join/:code', element: <Join /> },
  { path: '/l/:id/lobby', element: <Lobby /> },
  { path: '/l/:id/briefing', element: <Briefing /> },
  { path: '/l/:id/front', element: <Front /> },
  { path: '/l/:id/resupply', element: <Resupply /> },
  { path: '/l/:id/debrief/:week', element: <Debrief /> },
  { path: '/l/:id/campaign', element: <Campaign /> },
  { path: '/status', element: <Status /> },
]

// HashRouter: GitHub Pages has no SPA fallback.
export function App({ client = getSupabase() }: { client?: SupabaseClient | null }) {
  return (
    <AuthProvider client={client}>
      <ClockProvider>
        <HashRouter>
          <PendingRedirect />
          <Header />
          <DevBanner />
          <main id="main" tabIndex={-1}>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/login" element={<Login />} />
              <Route path="/rules" element={<Rules />} />
              <Route path="/debug" element={<Debug />} />
              {PRIVATE_ROUTES.map(({ path, element }) => (
                <Route key={path} path={path} element={<RequireAuth>{element}</RequireAuth>} />
              ))}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
          <BuildStamp />
        </HashRouter>
      </ClockProvider>
    </AuthProvider>
  )
}
