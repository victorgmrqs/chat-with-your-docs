---
title: Use React DOM Resource Hints
impact: HIGH
impactDescription: reduces load time for critical resources
tags: rendering, preload, preconnect, prefetch, resource-hints
---

## Use React DOM Resource Hints

**Impact: HIGH (reduces load time for critical resources)**

React DOM provides APIs to hint the browser about resources it will need. In a client-only SPA, `index.html` already ships before React runs, so use these for resources discovered later (for example third-party origins used only on some routes, or modules for a likely next navigation). Critical fonts and the entry stylesheet belong in `index.html` or the Vite build output, not here.

- **`prefetchDNS(href)`**: Resolve DNS for a domain you expect to connect to
- **`preconnect(href)`**: Establish connection (DNS + TCP + TLS) to a server
- **`preload(href, options)`**: Fetch a resource (stylesheet, font, script, image) you'll use soon
- **`preloadModule(href)`**: Fetch an ES module you'll use soon
- **`preinit(href, options)`**: Fetch and evaluate a stylesheet or script
- **`preinitModule(href)`**: Fetch and evaluate an ES module

**Example (preconnect to origins needed later):**

```tsx
import { preconnect, prefetchDNS } from 'react-dom'

export default function App() {
  // Hint origins that are only needed after this component renders
  prefetchDNS('https://cdn.example.com')
  preconnect('https://api.example.com')

  return <main>{/* content */}</main>
}
```

**Example (preload modules for code-split routes):**

```tsx
const loadDashboard = () => import('./routes/dashboard')

function Navigation() {
  // Vite hashes chunk file names, so preload through import(), not a fixed URL
  const preloadDashboard = () => {
    void loadDashboard()
  }

  return (
    <nav>
      <a href="/dashboard" onMouseEnter={preloadDashboard} onFocus={preloadDashboard}>
        Dashboard
      </a>
    </nav>
  )
}
```

**When to use each:**

| API | Use case |
|-----|----------|
| `prefetchDNS` | Third-party domains you'll connect to later |
| `preconnect` | APIs or CDNs you'll fetch from immediately |
| `preload` | Critical resources needed for current page |
| `preloadModule` | JS modules for likely next navigation |
| `preinit` | Stylesheets/scripts that must execute early |
| `preinitModule` | ES modules that must execute early |

Reference: [React DOM Resource Preloading APIs](https://react.dev/reference/react-dom#resource-preloading-apis)
