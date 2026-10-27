import { HashRouter, Route, Routes } from 'react-router'
import { Header } from '../components/Header'
import { Home } from '../pages/Home'
import { NotFound } from '../pages/NotFound'

// HashRouter: GitHub Pages has no SPA fallback.
export function App() {
  return (
    <HashRouter>
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </HashRouter>
  )
}
