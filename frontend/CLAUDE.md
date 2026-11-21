# frontend/ — React + Vite SPA

<!-- Facts only. Conventions: .claude/rules/frontend-*.md; vite and vitest skills. -->

- React 19, Vite 8, TypeScript 6, ESLint. Node 26. Dev dependencies pinned exactly.
- The app always calls the relative `/api` path:
  - dev: `vite.config.ts` proxies `/api` → `BACKEND_URL` (default `http://localhost:8000`,
    prefix stripped);
  - image: nginx proxies `/api/` → `${BACKEND_URL}/` (`nginx/default.conf.template`, resolved
    by envsubst at container start). Same image for Compose, homelab and cloud.
- Tests: Vitest + jsdom + Testing Library; setup in `src/test/setup.ts` (jest-dom matchers,
  explicit `cleanup` because `globals` is off). MSW is installed; the server lifecycle is added
  with the first API call.
- Tailwind v4 + shadcn/ui and design tokens arrive in CWYD-10; the page is a placeholder.

```bash
npm run lint && npm run typecheck && npm test
npm run build                    # tsc -b && vite build
npm run dev                      # :5173
```

- Image: `Dockerfile` (node:26-alpine build → nginx-unprivileged:1.30-alpine, port 8080).
