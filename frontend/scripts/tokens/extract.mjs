// Measures the raw values used by the design handoff and stores them in the `measured` block of
// docs/design-tokens.json. The named layers (primitive, semantic, component, merged) are
// hand-written and preserved: this script never decides a token name.
//
// The handoff lives in _docs/ (local, untracked), so this runs on a developer machine only.
// The audit (audit.mjs) reads the committed JSON and runs anywhere.
//
// Usage (from frontend/): npm run tokens:extract
import { existsSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { repoRoot, tokensFile } from './paths.mjs'

const designDir = join(repoRoot, '_docs/design')

const SCREENS = /^[1-5]-.*\.html$/ // the five screens; diagrams and the handoff note are not UI
const HEX = /#[0-9a-fA-F]{3,8}\b/g

/** Expands #fff to #FFFFFF so the same color is counted once. */
export function normalizeHex(hex) {
  const value = hex.slice(1).toUpperCase()
  return '#' + (value.length === 3 ? [...value].map((c) => c + c).join('') : value)
}

/** Every [property, value] pair in style="" attributes, <style> blocks and SVG paint attributes. */
export function declarations(html) {
  const inline = [...html.matchAll(/style="([^"]*)"/g)].map((m) => m[1])
  const blocks = [...html.matchAll(/<style>([\s\S]*?)<\/style>/g)].map((m) =>
    m[1].replace(/[^{}]*\{([^}]*)\}/g, '$1;'),
  )
  const pairs = [...inline, ...blocks]
    .flatMap((block) => block.split(';'))
    .map((decl) => decl.split(':'))
    .filter((parts) => parts.length >= 2)
    .map(([prop, ...rest]) => [prop.trim(), rest.join(':').trim()])
  const paint = [...html.matchAll(/\s(fill|stroke)="(#[0-9a-fA-F]{3,8})"/g)].map((m) => [m[1], m[2]])
  return [...pairs, ...paint]
}

function bump(group, value) {
  group[value] = (group[value] ?? 0) + 1
}

/** Sorts a { value: count } map by count, most used first. */
function byCount(group) {
  return Object.fromEntries(Object.entries(group).sort(([, a], [, b]) => b - a))
}

export function measure(htmlFiles) {
  const measured = { color: {}, fontSize: {}, radius: {}, lineHeight: {} }
  for (const html of htmlFiles) {
    for (const [prop, value] of declarations(html)) {
      for (const hex of value.match(HEX) ?? []) bump(measured.color, normalizeHex(hex))
      if (prop === 'font-size') bump(measured.fontSize, value)
      if (prop === 'line-height') bump(measured.lineHeight, value)
      if (prop === 'border-radius') {
        // "14px 14px 4px 14px" (chat bubble) is one component value made of primitive radii.
        for (const part of value.split(/\s+/)) bump(measured.radius, part)
      }
    }
  }
  return Object.fromEntries(Object.entries(measured).map(([k, v]) => [k, byCount(v)]))
}

function main() {
  const files = readdirSync(designDir)
    .filter((f) => SCREENS.test(f))
    .sort()
  const measured = measure(files.map((f) => readFileSync(join(designDir, f), 'utf8')))
  const current = existsSync(tokensFile) ? JSON.parse(readFileSync(tokensFile, 'utf8')) : {}
  const output = {
    $description: current.$description,
    $source: files.map((f) => `_docs/design/${f}`),
    measured,
    merged: current.merged ?? {},
    primitive: current.primitive ?? {},
    semantic: current.semantic ?? {},
    component: current.component ?? {},
  }
  writeFileSync(tokensFile, JSON.stringify(output, null, 2) + '\n')
  const total = Object.values(measured).reduce((n, g) => n + Object.keys(g).length, 0)
  console.log(`measured ${total} distinct values from ${files.length} screens → ${tokensFile}`)
}

if (process.argv[1] === fileURLToPath(import.meta.url)) main()
