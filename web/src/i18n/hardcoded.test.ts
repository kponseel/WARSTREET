// Milestone 09 i18n audit: no UI text written in a component. Every word a player reads
// comes from en.ts / fr.ts through t(). This parses each .tsx file and lists JSX text and
// text attributes (aria-label, title, alt, placeholder…) that contain letters.
import ts from 'typescript'
import { describe, expect, it } from 'vitest'

// Every component's source text, by path relative to src/ (Vite raw import).
const FILES = Object.entries(
  import.meta.glob<string>(['../**/*.tsx', '!../**/*.test.tsx'], { query: '?raw', import: 'default', eager: true }),
).map(([path, text]) => ({ path: path.replace('../', ''), text }))
const TEXT_ATTRIBUTES = new Set(['aria-label', 'aria-description', 'title', 'alt', 'placeholder', 'label'])
const LETTERS = /\p{L}{2,}/u

function hardcoded({ path, text }: { path: string; text: string }): string[] {
  const file = ts.createSourceFile(path, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
  const found: string[] = []
  const where = (node: ts.Node) => {
    const { line } = file.getLineAndCharacterOfPosition(node.getStart())
    return `${path}:${String(line + 1)}`
  }
  const visit = (node: ts.Node) => {
    if (ts.isJsxText(node) && LETTERS.test(node.text)) {
      found.push(`${where(node)} ${node.text.trim()}`)
    }
    if (
      ts.isJsxAttribute(node) &&
      TEXT_ATTRIBUTES.has(node.name.getText(file)) &&
      node.initializer &&
      ts.isStringLiteral(node.initializer) &&
      LETTERS.test(node.initializer.text)
    ) {
      found.push(`${where(node)} ${node.name.getText(file)}="${node.initializer.text}"`)
    }
    ts.forEachChild(node, visit)
  }
  visit(file)
  return found
}

describe('i18n audit', () => {
  it('finds the components', () => {
    expect(FILES.length).toBeGreaterThan(30)
  })

  it('has no hardcoded text in components (use t() and en.ts / fr.ts)', () => {
    expect(FILES.flatMap(hardcoded)).toEqual([])
  })
})
