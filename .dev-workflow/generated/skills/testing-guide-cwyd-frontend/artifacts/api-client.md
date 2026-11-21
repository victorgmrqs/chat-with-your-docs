> Part of the `testing-guide-cwyd-frontend` skill (see `../SKILL.md`).

# API client and MSW handlers (`src/api/**`, `src/**/handlers.ts`)

## What to test
- The contract compiles: the client (openapi-fetch) and the MSW handler bodies are typed from
  the generated schema (`src/api/schema.d.ts`, openapi-typescript), so a backend contract change
  fails `npm run typecheck` before any test runs.
- One round trip per endpoint through a consumer (component or hook test): the request reaches
  the expected path under `/api`, the response is parsed into what the UI renders.
- Error responses: the client surfaces the API error code the UI branches on.

## Layer assignment
- **Compile-time** (typecheck) for the contract shape.
- **Component tests** for round trips; no isolated "client returns JSON" unit tests (that would
  test openapi-fetch).
- **Playwright** proves the real `/api` path through nginx and the backend.

## Setup pattern
```ts
// src/api/handlers.ts — default happy-path handlers, typed from the schema
import { http, HttpResponse } from 'msw/http'
import type { components } from './schema'

type Document = components['schemas']['DocumentResponse']

export const handlers = [
  http.get('*/api/documents', () => HttpResponse.json<Document[]>([])),
]
```
- Type the body with the schema's component types (`HttpResponse.json<T>(...)`). A typed
  handler helper such as `openapi-msw` lists MSW 2 as its peer: check MSW 3 support before
  adding it (ask before installing).
- Match paths with a leading `*` (`*/api/...`) so handlers work whatever base URL the test
  environment resolves.

## When to skip
- Request serialization details owned by openapi-fetch.
- Handlers for endpoints no test exercises yet.

## Examples from project
- None yet. The client and schema generation arrive in CWYD-5.
