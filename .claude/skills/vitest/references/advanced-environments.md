---
name: test-environments
description: Configure the jsdom test environment for DOM APIs
---

# Test Environments

## Available Environments

- `node` (default) - Node.js environment
- `jsdom` - Browser-like with DOM APIs

## Configuration

```ts
// vitest.config.ts
defineConfig({
  test: {
    environment: 'jsdom',
    
    // Environment-specific options
    environmentOptions: {
      jsdom: {
        url: 'http://localhost',
      },
    },
  },
})
```

## Installing Environment Packages

```bash
# jsdom (ask the user first; never install without approval)
npm i -D jsdom
```

## Per-File Environment

Use magic comment at top of file:

```ts
// @vitest-environment jsdom

import { expect, test } from 'vitest'

test('DOM test', () => {
  const div = document.createElement('div')
  expect(div).toBeInstanceOf(HTMLDivElement)
})
```

## jsdom Environment

Full browser environment simulation:

```ts
// @vitest-environment jsdom

test('DOM manipulation', () => {
  document.body.innerHTML = '<div id="app"></div>'
  
  const app = document.getElementById('app')
  app.textContent = 'Hello'
  
  expect(app.textContent).toBe('Hello')
})

test('window APIs', () => {
  expect(window.location.href).toBeDefined()
  expect(localStorage).toBeDefined()
})
```

### jsdom Options

```ts
defineConfig({
  test: {
    environmentOptions: {
      jsdom: {
        url: 'http://localhost:3000',
        html: '<!DOCTYPE html><html><body></body></html>',
        userAgent: 'custom-agent',
        resources: 'usable',
      },
    },
  },
})
```

## Multiple Environments per Project

Use projects for different environments:

```ts
defineConfig({
  test: {
    projects: [
      {
        test: {
          name: 'unit',
          include: ['tests/unit/**/*.test.ts'],
          environment: 'node',
        },
      },
      {
        test: {
          name: 'dom',
          include: ['tests/dom/**/*.test.ts'],
          environment: 'jsdom',
        },
      },
    ],
  },
})
```

## Custom Environment

Create custom environment package:

```ts
// vitest-environment-custom/index.ts
import type { Environment } from 'vitest/runtime'

export default <Environment>{
  name: 'custom',
  viteEnvironment: 'ssr', // or 'client'
  
  setup() {
    // Setup global state
    globalThis.myGlobal = 'value'
    
    return {
      teardown() {
        delete globalThis.myGlobal
      },
    }
  },
}
```

Use with:

```ts
defineConfig({
  test: {
    environment: 'custom',
  },
})
```

## Environment with VM

For full isolation:

```ts
export default <Environment>{
  name: 'isolated',
  viteEnvironment: 'ssr',
  
  async setupVM() {
    const vm = await import('node:vm')
    const context = vm.createContext()
    
    return {
      getVmContext() {
        return context
      },
      teardown() {},
    }
  },
  
  setup() {
    return { teardown() {} }
  },
}
```

> v5: DOM-environment global assignments (e.g. `window.innerWidth`) now propagate to the underlying jsdom implementation. Real-browser testing belongs to Playwright E2E in this project, not Vitest Browser Mode.

## CSS and Assets

In jsdom, configure CSS handling:

```ts
defineConfig({
  test: {
    css: true, // Process CSS
    
    // Or with options
    css: {
      include: /\.module\.css$/,
      modules: {
        classNameStrategy: 'non-scoped',
      },
    },
  },
})
```

## Fixing External Dependencies

If external deps fail with CSS/asset errors:

```ts
defineConfig({
  test: {
    server: {
      deps: {
        inline: ['problematic-package'],
      },
    },
  },
})
```

## Key Points

- Default is `node` - no browser APIs
- Use `jsdom` for full browser simulation
- Per-file environment via `// @vitest-environment` comment
- Use projects for multiple environment configurations
- Real-browser testing is done with Playwright E2E, not Vitest

<!-- 
Source references:
- https://vitest.dev/guide/environment.html
-->
