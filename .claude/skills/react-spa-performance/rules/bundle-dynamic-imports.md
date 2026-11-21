---
title: Dynamic Imports for Heavy Components
impact: CRITICAL
impactDescription: directly affects TTI and LCP
tags: bundle, dynamic-import, code-splitting, react-lazy
---

## Dynamic Imports for Heavy Components

Use `React.lazy` with `<Suspense>` to lazy-load large components not needed on initial render. Vite turns each `import()` into a separate chunk.

**Incorrect (Monaco bundles with main chunk ~300KB):**

```tsx
import { MonacoEditor } from './monaco-editor'

function CodePanel({ code }: { code: string }) {
  return <MonacoEditor value={code} />
}
```

**Correct (Monaco loads on demand):**

```tsx
import { lazy, Suspense } from 'react'

const MonacoEditor = lazy(() =>
  import('./monaco-editor').then(m => ({ default: m.MonacoEditor }))
)

function CodePanel({ code }: { code: string }) {
  return (
    <Suspense fallback={<div className="h-64 animate-pulse bg-muted" />}>
      <MonacoEditor value={code} />
    </Suspense>
  )
}
```

Define the `lazy()` call at module level, never inside a component, otherwise the component remounts on every render. Route-level components are the best first candidates for splitting.
