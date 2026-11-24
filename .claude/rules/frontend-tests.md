---
paths:
  - "frontend/**/*.test.ts"
  - "frontend/**/*.test.tsx"
  - "frontend/e2e/**"
---

# Frontend tests

- Unit and component tests: Vitest + Testing Library (jsdom). Query by role and accessible name;
  interact with `user-event`; assert what the user sees.
- Network is mocked with MSW handlers typed from the OpenAPI schema. Never `vi.stubGlobal('fetch')`
  and never mock the API client module.
- Each component covers the happy path plus the error and empty states it renders (failed
  upload, indexing failed, "not enough evidence" answer).
- No snapshot tests of whole components; small inline snapshots only for formatted values.
- E2E: Playwright against the Docker Compose stack, headless by default, driven through the
  Playwright CLI. Base URL and any credentials come from env or fixtures, never literals.
- E2E artifacts (traces, auth state, reports) are never committed; they may contain tokens.
- Fake timers only for polling logic; always restore real timers in `afterEach`.
