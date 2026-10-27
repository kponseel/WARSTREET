// Avatar letters stay readable on every avatar colour (WCAG contrast formula).
/** Black or white, whichever reads better on a background colour (#rrggbb). */
export function textOn(hex: string): string {
  const channel = (i: number) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  }
  const luminance = 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5)
  // Contrast with white is (1.05)/(L+0.05); with black (L+0.05)/0.05.
  return 1.05 / (luminance + 0.05) >= (luminance + 0.05) / 0.05 ? '#ffffff' : '#14181f'
}
