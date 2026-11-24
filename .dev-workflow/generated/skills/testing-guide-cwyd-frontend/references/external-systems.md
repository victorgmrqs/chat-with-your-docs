> Part of the `testing-guide-cwyd-frontend` skill (see `../SKILL.md`).

# External systems

| System | Strategy | How |
|---|---|---|
| Backend API (`/api`) in Vitest | **Fake** | MSW 3 `setupServer` (`msw/node`), handlers typed from the OpenAPI schema |
| Backend API in E2E | **Real** | Playwright against `docker compose up --build --wait` |
| Streaming answers | **Fake** (Vitest) | `msw/sse` handlers with scripted events |
| Browser | jsdom (Vitest); Chromium headless (Playwright) | — |

## MSW server (shared)
```ts
// src/test/server.ts
import { setupServer } from 'msw/node'
import { handlers } from '../api/handlers'
export const server = setupServer(...handlers)

// src/test/setup.ts (added with the first API call)
beforeAll(() => server.listen({ onUnhandledFrame: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```
- `onUnhandledFrame` is MSW 3's name for the old `onUnhandledRequest`; values `'error' | 'warn'
  | 'bypass'`.
- Per-test overrides with `server.use(...)` are reset after each test.

## Backend in E2E
- The stack is the evaluator's stack: same images, same nginx proxy. Base URL comes from env
  (`http://localhost:8080` locally; `host.docker.internal:8080` from the dev container).
