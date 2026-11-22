// @vitest-environment node
import { describe, expect, it } from 'vitest'

import { renderTheme } from './apply.mjs'
import { audit, findCnDrift, findDrift, findHardcoded, findMissing } from './audit.mjs'

const tokens = {
  measured: { color: { '#2952CC': 3, '#EDEDEA': 1 }, fontSize: { '12px': 2 }, radius: {}, lineHeight: {} },
  merged: { color: { '#EDEDEA': '#F0F0EE' } },
  primitive: {
    color: { 'blue-600': '#2952CC', 'gray-100': '#F0F0EE' },
    fontSize: { caption: '12px' },
    radius: { lg: '10px' },
    lineHeight: { normal: '1.5' },
    fontFamily: { sans: 'Inter' },
    letterSpacing: { eyebrow: '0.06em' },
  },
  semantic: { color: { primary: 'blue-600' } },
  component: { color: { citation: 'primary' } },
}

describe('design tokens', () => {
  it('design_tokens_no_drift', () => {
    expect(audit()).toEqual({ missing: [], drift: [], hardcoded: [] })
  })

  it('reports a measured value without a primitive and a broken reference', () => {
    const broken = structuredClone(tokens)
    broken.measured.color['#123456'] = 1
    broken.component.color.bubble = 'secondary'

    expect(findMissing(broken)).toEqual([
      'color #123456 has no primitive token',
      'component color bubble references unknown semantic secondary',
    ])
  })

  it('reports a theme value that differs from the token file', () => {
    const theme = renderTheme(tokens).replace('#2952CC', '#2952CD')

    expect(findDrift(tokens, theme)).toEqual(['--blue-600 is "#2952CD" in theme.css, expected "#2952CC"'])
  })

  it('reports a custom scale missing from createCn', () => {
    const utils = "theme: { text: [], leading: ['normal'], tracking: ['eyebrow'] }"

    expect(findCnDrift(tokens, utils)).toEqual(['createCn text is [], expected [caption]'])
  })

  it('reports raw colors, default palette, arbitrary sizes, unknown radii and shadows', () => {
    const file = [
      'src/x.tsx',
      '<div className="bg-gray-200 text-[13px] rounded-4xl shadow-sm" style={{ color: "#fff" }} />',
    ]

    expect(findHardcoded([file], new Set(['lg']))).toEqual([
      'src/x.tsx:1 raw hex color: #fff',
      'src/x.tsx:1 default Tailwind palette: bg-gray-200',
      'src/x.tsx:1 arbitrary font size, radius or line height: text-[13px]',
      'src/x.tsx:1 shadow (borders carry the hierarchy): shadow-sm',
      'src/x.tsx:1 radius without a token: rounded-4xl',
    ])
  })
})
