import { GAME_NAME } from '../config'
import { useI18n } from '../i18n/context'
import { getSupabase } from '../lib/supabase'

export function Home() {
  const { t } = useI18n()
  const backendReady = getSupabase() !== null
  return (
    <section className="page">
      <h1>{t('home.title', { game: GAME_NAME })}</h1>
      <p className="lead">{t('app.tagline')}</p>
      <p>{t('home.intro')}</p>
      <p className="notice">{t('home.comingSoon')}</p>
      <p className={backendReady ? 'status status-ok' : 'status status-missing'}>
        {t(backendReady ? 'home.backend.ok' : 'home.backend.missing')}
      </p>
    </section>
  )
}
