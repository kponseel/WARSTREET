import { useState } from 'react'
import { useI18n } from '../i18n/context'

export function CopyButton({ text, label }: { text: string; label: string }) {
  const { t } = useI18n()
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      className="button button-secondary"
      onClick={() => {
        void navigator.clipboard.writeText(text).then(
          () => {
            setCopied(true)
          },
          () => {
            setCopied(false)
          },
        )
      }}
    >
      {label}
      <span className="sr-live" aria-live="polite">
        {copied ? ` · ${t('common.copied')}` : ''}
      </span>
    </button>
  )
}
