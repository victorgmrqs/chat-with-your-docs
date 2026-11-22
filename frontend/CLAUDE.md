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
- `App.tsx` is still a placeholder; CWYD-5 wires the components to the API.

```bash
npm run lint && npm run typecheck && npm test
npm run build                    # tsc -b && vite build
npm run dev                      # :5173 (/preview.html: design preview)
npm run tokens:audit             # tokens: missing / drift / hardcoded
```

- Image: `Dockerfile` (node:26-alpine build → nginx-unprivileged:1.30-alpine, port 8080).

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
- Primitives in `src/components/ui/` were adapted to the tokens (44px targets, borders, no shadow);
  domain components in `src/components/` take data and callbacks only (no fetching).
- `npm run dev` → `/preview.html#<screen>` composes the five handoff screens from static fixtures
  (`src/preview/`); compare with `_docs/design/*.png` after any visual change.
