---
title: Prefer Statically Analyzable Paths
impact: HIGH
impactDescription: avoids accidental broad bundles and file traces
tags: bundle, vite, rollup, esbuild, path
---

## Prefer Statically Analyzable Paths

Build tools work best when import and file-system paths are obvious at build time. If you hide the real path inside a variable or compose it too dynamically, the tool either has to include a broad set of possible files, warn that it cannot analyze the import, or widen file tracing to stay safe.

Prefer explicit maps or literal paths so the set of reachable files stays narrow and predictable. This is the same rule whether you are choosing modules with `import()` or using `import.meta.glob`.

When analysis becomes too broad, the cost is real:
- Larger bundles
- Slower builds
- Worse load times
- More memory use

### Import Paths

**Incorrect (the bundler cannot tell what may be imported):**

```ts
const PAGE_MODULES = {
  home: './pages/home',
  settings: './pages/settings',
} as const

const Page = await import(PAGE_MODULES[pageName])
```

**Correct (use an explicit map of allowed modules):**

```ts
const PAGE_MODULES = {
  home: () => import('./pages/home'),
  settings: () => import('./pages/settings'),
} as const

const Page = await PAGE_MODULES[pageName]()
```

### Vite Glob Imports

**Incorrect (a computed pattern cannot be analyzed):**

```ts
const modules = import.meta.glob(`./locales/${dir}/*.json`)
```

**Correct (literal pattern, then select by key):**

```ts
const modules = import.meta.glob('./locales/*/*.json')
const loader = modules[`./locales/${locale}/messages.json`]
```

Reference: [Vite features](https://vite.dev/guide/features.html), [esbuild API](https://esbuild.github.io/api/), [Rollup dynamic import vars](https://www.npmjs.com/package/@rollup/plugin-dynamic-import-vars)
