---
name: vite
description: Vite configuration for this project's React SPA: vite.config.ts, env vars (import.meta.env, VITE_ prefix), assets and glob imports, dev server proxy to the FastAPI backend. Use when editing vite.config.ts or Vite-related frontend setup. Not for SSR, library mode or Vue.
license: MIT
metadata:
  author: Anthony Fu
  version: "2026.11.5"
  source: Adapted from https://github.com/antfu/skills (skills/vite), see SOURCE.md
---

# Vite

## Project overrides

These rules come from the project and win over anything below.

- The frontend is a React + Vite + TypeScript SPA: no SSR, no library mode, no Vue. Ignore any SSR or library-mode option you see in Vite docs.
- Run the dev server with a proxy for the backend (`server.proxy` -> FastAPI service) instead of hardcoding backend URLs in code. Only variables prefixed with `VITE_` are exposed to client code through `import.meta.env`; never put secrets in `VITE_*` variables.
- Never install packages or plugins (`@vitejs/plugin-react`, etc.) without asking the user first.
- Vite and Vitest share the config: tests run through Vitest, see the `vitest` skill.
- This skill targets Vite 8 (Rolldown bundler and Oxc transformer instead of Rollup + esbuild). Exact versions are chosen when the frontend is scaffolded: verify version-specific claims (e.g. `build.rolldownOptions`, top-level `input`) against the version in `frontend/package.json`.

Vite is a frontend build tool with a fast dev server (native ESM + HMR) and optimized production builds.

## Preferences

- Use TypeScript: prefer `vite.config.ts`
- Always use ESM, avoid CommonJS

## Core

| Topic | Description | Reference |
|-------|-------------|-----------|
| Configuration | `vite.config.ts`, `defineConfig`, conditional configs, `loadEnv` | [core-config](references/core-config.md) |
| Features | `import.meta.glob`, asset queries (`?raw`, `?url`), `import.meta.env`, HMR API | [core-features](references/core-features.md) |

## Quick Reference

### CLI Commands

```bash
vite              # Start dev server
vite build        # Production build
vite preview      # Preview production build
```

### Common Config

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': '/src' } },
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } },
  build: { outDir: 'dist' },
})
```

### Official Plugins

- `@vitejs/plugin-react` - React with Oxc/Babel (ask the user before installing)
- `@vitejs/plugin-legacy` - Legacy browser support (only if a requirement exists)
