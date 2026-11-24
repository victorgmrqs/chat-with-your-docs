---
title: Preload Based on User Intent
impact: MEDIUM
impactDescription: reduces perceived latency
tags: bundle, preload, user-intent, hover
---

## Preload Based on User Intent

Preload heavy bundles before they're needed to reduce perceived latency. Calling `import()` again later resolves from the module cache, so a `React.lazy` component renders instantly once preloaded.

**Example (preload on hover/focus):**

```tsx
const loadEditor = () => import('./monaco-editor')
const MonacoEditor = lazy(() =>
  loadEditor().then(m => ({ default: m.MonacoEditor }))
)

function EditorButton({ onClick }: { onClick: () => void }) {
  const preload = () => {
    void loadEditor()
  }

  return (
    <button
      onMouseEnter={preload}
      onFocus={preload}
      onClick={onClick}
    >
      Open Editor
    </button>
  )
}
```

**Example (preload when feature flag is enabled):**

```tsx
function FlagsProvider({ children, flags }: Props) {
  useEffect(() => {
    if (flags.editorEnabled) {
      void import('./monaco-editor').then(mod => mod.init())
    }
  }, [flags.editorEnabled])

  return <FlagsContext.Provider value={flags}>
    {children}
  </FlagsContext.Provider>
}
```
