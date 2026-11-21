> Part of the `testing-guide-cwyd-frontend` skill (see `../SKILL.md`).

# File conventions

```
frontend/
  vite.config.ts       # test: { environment: 'jsdom', setupFiles: ['./src/test/setup.ts'] }
  src/
    test/setup.ts      # jest-dom matchers, cleanup, MSW lifecycle, jsdom stubs
    test/server.ts     # shared MSW server (added with the first API call)
    api/handlers.ts    # default happy-path handlers
    <Feature>.tsx
    <Feature>.test.tsx # colocated component test
  e2e/                 # Playwright specs and fixtures (CWYD-8)
```

- Component and hook tests: `*.test.tsx` / `*.test.ts`, colocated with the code.
- Test names describe the visible behavior: `it('shows the failure reason when indexing failed')`.
- `globals: false`: import `describe`, `it`, `expect`, `vi`, hooks from `vitest` in every file.
- `src/test/setup.ts` imports `@testing-library/jest-dom/vitest` (typed matchers) and registers
  `afterEach(() => cleanup())`.
- Test files live under `src/`, so they are typechecked by `tsc -b` with the app.
- Coverage: no percentage target (pragmatic policy). The §3 checklist in `../SKILL.md` is the
  gate.

## Commands (from `frontend/`)

```bash
npm test                     # vitest run
npx vitest                   # watch mode while developing (ask before using npx in automation)
npm run typecheck            # also validates typed MSW handlers against the schema
```
