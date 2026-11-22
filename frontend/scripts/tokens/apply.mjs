// Writes src/styles/theme.css from docs/design-tokens.json (primitive, semantic, component).
// Edit tokens in the JSON, then run `npm run tokens:apply && npm run tokens:audit`.
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { themeFile, tokensFile } from './paths.mjs'

// Tailwind namespaces reset so that only our tokens exist as utilities (no default palette,
// no default font sizes or radii, no shadows: DOM-14).
const RESET = ['color', 'text', 'radius', 'leading', 'shadow', 'inset-shadow', 'drop-shadow', 'text-shadow']

export function renderTheme(tokens) {
  const { primitive, semantic, component } = tokens
  const colors = { ...semantic.color, ...component.color }
  const lines = [
    '/* Design tokens (light theme only). Generated from docs/design-tokens.json by',
    ' * scripts/tokens/apply.mjs; do not edit by hand. `npm run tokens:audit` fails on any drift.',
    ' * Primitives are plain variables; only semantic and component colors become utilities,',
    ' * so components never reach a raw palette value. */',
    ':root {',
    '  /* Primitive */',
    ...Object.entries(primitive.color).map(([name, hex]) => `  --${name}: ${hex};`),
    '',
    '  /* Semantic */',
    ...Object.entries(semantic.color).map(([name, ref]) => `  --${name}: var(--${ref});`),
    '',
    '  /* Component */',
    ...Object.entries(component.color).map(([name, ref]) => `  --${name}: var(--${ref});`),
    '}',
    '',
    '@theme inline {',
    ...RESET.map((ns) => `  --${ns}-*: initial;`),
    '',
    ...Object.keys(colors).map((name) => `  --color-${name}: var(--${name});`),
    '',
    ...Object.entries(primitive.fontFamily).map(([name, v]) => `  --font-${name}: ${v};`),
    ...Object.entries(primitive.letterSpacing).map(([name, v]) => `  --tracking-${name}: ${v};`),
    '',
    ...Object.entries(primitive.fontSize).map(([name, v]) => `  --text-${name}: ${v};`),
    '',
    ...Object.entries(primitive.lineHeight).map(([name, v]) => `  --leading-${name}: ${v};`),
    '',
    ...Object.entries(primitive.radius).map(([name, v]) => `  --radius-${name}: ${v};`),
    '}',
  ]
  return lines.join('\n') + '\n'
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  writeFileSync(themeFile, renderTheme(JSON.parse(readFileSync(tokensFile, 'utf8'))))
  console.log(`wrote ${themeFile}`)
}
