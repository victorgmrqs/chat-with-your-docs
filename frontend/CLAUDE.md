# frontend/ — React + Vite SPA

<!-- Facts only. Conventions: .claude/rules/frontend-*.md; vite and vitest skills. -->

- React 19, Vite 8, TypeScript 6, ESLint. Node 26. Dev dependencies pinned exactly.
- The app always calls the relative `/api` path:
  - dev: `vite.config.ts` proxies `/api` → `BACKEND_URL` (default `http://localhost:8000`,
    prefix stripped);
  - image: nginx proxies `/api/` → `${BACKEND_URL}/` (`nginx/default.conf.template`, resolved
    by envsubst at container start). Same image for Compose, homelab and cloud.
- API (CWYD-5): `src/api/client.ts` is the only way to the API: openapi-fetch typed by
  `src/api/schema.d.ts`, generated from `openapi.json` (both committed). After a backend API
  change: `cd backend && uv run python -m scripts.export_openapi`, then `npm run api:types`.
  `unwrap()` returns the data or throws `ApiError` (`status`, the backend `detail` as message;
  `transient` for network/5xx, DOM-18). `openapi-typescript` declares a TS 5 peer; the
  `overrides` entry in `package.json` runs it on the project's TS 6.
- Server state lives in `src/hooks/`: `useDocuments` (list + polling, DOM-19), `useUpload`
  (multipart, rejections, files kept for retry), `useChat` (turns, retry, DOM-18). `App.tsx`
  composes them with the components; API → view mapping is in `src/lib/{documents,chat}.ts`.
- MSW (`src/mocks/`): typed payload builders (`data.ts`), an in-memory backend (`db.ts`,
  time-based indexing, `finishIndexing()`), handlers by domain (`handlers/`). Vitest uses
  `server.ts`; `VITE_API_MOCKS=true npm run dev` runs the app on `browser.ts` without the
  backend (worker served by the `msw/vite` plugin; demo triggers in `db.ts` and
  `handlers/chat.ts`).
- Tests: Vitest + jsdom + Testing Library; setup in `src/test/setup.ts` (jest-dom matchers,
  explicit `cleanup` because `globals` is off, MSW server with `onUnhandledFrame: 'error'`,
  5 s `findBy*` wait; 15 s test timeout in `vite.config.ts`). A test never leaves a mocked
  request pending: it stalls the next test's requests.
  `vitest.node-globals.ts` runs first and swaps jsdom's Blob/File/FormData and Vitest's compat
  Request for Node's: without it multipart uploads never reach MSW. Polling tests use real
  timers with a short `useDocuments(intervalMs)`: under fake timers the request pipeline
  stalls.

```bash
npm run lint && npm run typecheck && npm test
npm run build                    # tsc -b && vite build
npm run dev                      # :5173 (/preview.html: design preview)
npm run tokens:audit             # tokens: missing / drift / hardcoded
npm run api:types                # openapi.json → src/api/schema.d.ts
VITE_API_MOCKS=true npm run dev  # app on MSW, no backend
```

- Image: `Dockerfile` (node:26-alpine build → nginx-unprivileged:1.31-alpine mainline, port 8080).

## Design system

- Tokens: `docs/design-tokens.json` is the source (primitive → semantic → component, plus the
  `measured` handoff values and the near-duplicates `merged` into a primitive).
  `src/styles/theme.css` is generated from it: change the JSON, run `npm run tokens:apply`, then
  `npm run tokens:audit` (also a Vitest test). Never edit the theme by hand.
- Only semantic and component colors are utilities (`bg-primary`, `text-muted-foreground`,
  `bg-status-ready`); Tailwind's default palette, font sizes, radii and shadows are reset.
- Font sizes are named (`text-caption` 12 … `text-display` 28); radii `rounded-xs` 4 …
  `rounded-3xl` 16, `rounded-lg` (10px) is the default. A new custom scale value must also be
  registered in `createCn` (`src/lib/utils.ts`), or `cn()` drops it as a conflicting text color;
  the audit reports a mismatch as drift.
- No hex, no arbitrary `text-[…]`/`rounded-[…]`/`leading-[…]`, no `shadow-*`, no `dark:`: the audit
  fails on them.
- Layout (`AppLayout`): from `md` up an app shell of the viewport's height: the page never
  scrolls, the sidebar stays fixed (own scroll for long lists) and only the conversation scrolls
  (`ChatThread`, which scrolls to the latest turn on send and on answer); the question input stays
  at the bottom. Below `md` the columns stack and the page scrolls.
- Focus: one global `:focus-visible` style in `src/index.css` (solid 2px outline in the `ring`
  token, 2px offset). Components do not add their own focus rings.
- Primitives in `src/components/ui/` were adapted to the tokens (44px targets, borders, no shadow);
  domain components in `src/components/` take data and callbacks only (no fetching).
- `npm run dev` → `/preview.html#<screen>` composes the five handoff screens from static fixtures
  (`src/preview/`); compare with `_docs/design/*.png` after any visual change.
