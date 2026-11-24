// Checks that the theme, the token file and the components agree. Three kinds of problem:
//   missing   — a value measured in the handoff has no primitive (and was not merged into one);
//   drift     — src/styles/theme.css differs from what docs/design-tokens.json describes;
//   hardcoded — a component uses a raw color, an arbitrary size/radius, the default palette,
//               a shadow or a dark variant instead of a token.
// Drift also covers src/lib/utils.ts: the custom scales registered in `createCn` must be exactly
// the token names, or cn() silently drops classes it does not know.
// Usage (from frontend/): npm run tokens:audit   (exit code 1 on any problem)
import { readdirSync, readFileSync } from 'node:fs'
import { join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

import { renderTheme } from './apply.mjs'
import { cnFile, frontendRoot, themeFile, tokensFile } from './paths.mjs'

const srcDir = join(frontendRoot, 'src')

// Groups measured in the handoff; each has a primitive group of the same name.
const MEASURED_GROUPS = ['color', 'fontSize', 'radius', 'lineHeight']

export function findMissing(tokens) {
  const missing = []
  for (const group of MEASURED_GROUPS) {
    const values = new Set(Object.values(tokens.primitive[group]).map((v) => v.toUpperCase()))
    const merged = tokens.merged[group] ?? {}
    for (const value of Object.keys(tokens.measured[group] ?? {})) {
      const target = merged[value]
      if (target && !values.has(target.toUpperCase())) {
        missing.push(`${group} ${value} is merged into ${target}, which is not a primitive`)
      } else if (!target && !values.has(value.toUpperCase())) {
        missing.push(`${group} ${value} has no primitive token`)
      }
    }
  }
  for (const [layer, below] of [
    ['semantic', 'primitive'],
    ['component', 'semantic'],
  ]) {
    for (const [name, ref] of Object.entries(tokens[layer].color)) {
      if (!(ref in tokens[below].color)) missing.push(`${layer} color ${name} references unknown ${below} ${ref}`)
    }
  }
  return missing
}

/** `--name: value` declarations of a stylesheet, in order. */
function declarations(css) {
  return [...css.matchAll(/--([\w-]+(?:\*)?)\s*:\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()])
}

export function findDrift(tokens, themeCss) {
  const expected = new Map(declarations(renderTheme(tokens)))
  const actual = new Map(declarations(themeCss))
  const drift = []
  for (const [name, value] of expected) {
    if (!actual.has(name)) drift.push(`--${name} is missing from theme.css`)
    else if (actual.get(name).toUpperCase() !== value.toUpperCase())
      drift.push(`--${name} is "${actual.get(name)}" in theme.css, expected "${value}"`)
  }
  for (const name of actual.keys()) {
    if (!expected.has(name)) drift.push(`--${name} is declared in theme.css but not in design-tokens.json`)
  }
  return drift
}

// createCn theme key → token group
const CN_SCALES = { text: 'fontSize', leading: 'lineHeight', tracking: 'letterSpacing' }

/** The custom scales registered in `createCn({ extend: { theme: … } })` must match the tokens. */
export function findCnDrift(tokens, utilsSource) {
  const drift = []
  for (const [key, group] of Object.entries(CN_SCALES)) {
    const match = utilsSource.match(new RegExp(`\\b${key}:\\s*\\[([^\\]]*)\\]`))
    const registered = match ? [...match[1].matchAll(/'([^']+)'/g)].map((m) => m[1]) : []
    const expected = Object.keys(tokens.primitive[group])
    if (registered.join() !== expected.join())
      drift.push(`createCn ${key} is [${registered.join(', ')}], expected [${expected.join(', ')}]`)
  }
  return drift
}

const PALETTE =
  'slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|black|white'
const HARDCODED = [
  [/#[0-9a-fA-F]{3,8}\b/, 'raw hex color'],
  [/\b(?:rgba?|hsla?|oklch|oklab)\(/, 'raw color function'],
  [new RegExp(`\\b(?:bg|text|border|ring|outline|fill|stroke|from|to|via|decoration|divide|placeholder|accent|caret)-(?:${PALETTE})(?:-\\d{2,3})?\\b`), 'default Tailwind palette'],
  [/\b(?:text|rounded(?:-[trblse]{1,2})?|leading)-\[[^\]]+\]/, 'arbitrary font size, radius or line height'],
  [/\btext-(?:xs|sm|base|lg|xl|[2-9]xl)\b/, 'Tailwind default font size instead of a token'],
  [/\bleading-(?:none|tight|loose|\d+)\b/, 'Tailwind default line height instead of a token'],
  [/\bshadow(?:-[\w/[\]-]+)?\b/, 'shadow (borders carry the hierarchy)'],
  [/\bdark:/, 'dark variant (light theme only)'],
]

function sourceFiles(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) return sourceFiles(path)
    return /\.(tsx?|css)$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name) ? [path] : []
  })
}

/** Radius utilities must use a radius token name (`rounded-lg` is our 10px, not Tailwind's). */
function unknownRadius(line, radiusNames) {
  return [...line.matchAll(/\brounded(?:-[trblse]{1,2})?-([\w]+)\b/g)]
    .map((m) => m[0])
    .find((cls) => !radiusNames.has(cls.split('-').at(-1)))
}

export function findHardcoded(files, radiusNames = new Set()) {
  const allowed = new Set([...radiusNames, 'none', 'full'])
  const problems = []
  for (const [file, text] of files) {
    text.split('\n').forEach((line, index) => {
      if (/^\s*(\/\/|\*|\/\*)/.test(line)) return // comments may mention what is forbidden
      for (const [pattern, reason] of HARDCODED) {
        const match = line.match(pattern)
        if (match) problems.push(`${file}:${index + 1} ${reason}: ${match[0]}`)
      }
      const radius = unknownRadius(line, allowed)
      if (radius) problems.push(`${file}:${index + 1} radius without a token: ${radius}`)
    })
  }
  return problems
}

export function audit() {
  const tokens = JSON.parse(readFileSync(tokensFile, 'utf8'))
  const files = sourceFiles(srcDir)
    .filter((path) => path !== themeFile)
    .map((path) => [relative(frontendRoot, path), readFileSync(path, 'utf8')])
  return {
    missing: findMissing(tokens),
    drift: [
      ...findDrift(tokens, readFileSync(themeFile, 'utf8')),
      ...findCnDrift(tokens, readFileSync(cnFile, 'utf8')),
    ],
    hardcoded: findHardcoded(files, new Set(Object.keys(tokens.primitive.radius))),
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const result = audit()
  let failed = false
  for (const [kind, problems] of Object.entries(result)) {
    console.log(`${kind}: ${problems.length}`)
    for (const problem of problems) console.log(`  - ${problem}`)
    failed ||= problems.length > 0
  }
  process.exit(failed ? 1 : 0)
}
