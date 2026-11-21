---
title: Deduplicate Global Event Listeners
impact: LOW
impactDescription: single listener for N components
tags: client, event-listeners, subscription
---

## Deduplicate Global Event Listeners

Share one global event listener across component instances with a module-level registry.

**Incorrect (N instances = N listeners):**

```tsx
function useKeyboardShortcut(key: string, callback: () => void) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.metaKey && e.key === key) {
        callback()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [key, callback])
}
```

When using the `useKeyboardShortcut` hook multiple times, each instance will register a new listener.

**Correct (N instances = 1 listener):**

```tsx
// Module-level Map to track callbacks per key
const keyCallbacks = new Map<string, Set<() => void>>()
let removeListener: (() => void) | null = null

function handler(e: KeyboardEvent) {
  if (e.metaKey) {
    keyCallbacks.get(e.key)?.forEach(cb => cb())
  }
}

function subscribe(key: string, callback: () => void) {
  if (!keyCallbacks.has(key)) {
    keyCallbacks.set(key, new Set())
  }
  keyCallbacks.get(key)!.add(callback)

  // First subscriber installs the single shared listener
  if (!removeListener) {
    window.addEventListener('keydown', handler)
    removeListener = () => window.removeEventListener('keydown', handler)
  }

  return () => {
    const set = keyCallbacks.get(key)
    if (set) {
      set.delete(callback)
      if (set.size === 0) keyCallbacks.delete(key)
    }
    // Last subscriber removes the shared listener
    if (keyCallbacks.size === 0 && removeListener) {
      removeListener()
      removeListener = null
    }
  }
}

function useKeyboardShortcut(key: string, callback: () => void) {
  useEffect(() => subscribe(key, callback), [key, callback])
}

function Profile() {
  // Multiple shortcuts will share the same listener
  useKeyboardShortcut('p', () => { /* ... */ })
  useKeyboardShortcut('k', () => { /* ... */ })
  // ...
}
```
