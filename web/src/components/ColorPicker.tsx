import type { CSSProperties } from 'react'
import { useI18n } from '../i18n/context'

export function ColorPicker({
  colors,
  value,
  onChange,
  name = 'avatar-color',
}: {
  colors: string[]
  value: string | null
  onChange: (color: string) => void
  name?: string
}) {
  const { t } = useI18n()
  return (
    <fieldset className="color-picker">
      <legend>{t('member.color')}</legend>
      <div className="color-swatches">
        {colors.map((color, index) => (
          <label key={color} className="swatch" style={{ '--swatch': color } as CSSProperties}>
            <input
              type="radio"
              name={name}
              value={color}
              checked={value === color}
              aria-label={t('member.colorOption', { n: index + 1 })}
              onChange={() => {
                onChange(color)
              }}
            />
            <span className="swatch-dot" aria-hidden="true" />
          </label>
        ))}
      </div>
    </fieldset>
  )
}
