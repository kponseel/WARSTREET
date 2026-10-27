import { Link } from 'react-router'
import { useI18n } from '../i18n/context'

export function NotFound() {
  const { t } = useI18n()
  return (
    <section className="page">
      <h1>{t('notFound.title')}</h1>
      <p>
        <Link to="/">{t('notFound.back')}</Link>
      </p>
    </section>
  )
}
