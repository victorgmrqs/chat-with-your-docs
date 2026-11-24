---
paths:
  - "frontend/src/**/*.tsx"
  - "frontend/src/**/*.ts"
---

# Frontend components

- React + Vite SPA, TypeScript strict. No Next.js APIs, no SSR, no server components.
- Styling: Tailwind v4 classes that map to design tokens declared in `@theme` (hex values,
  light theme only). Never hardcode colors, never use the default Tailwind palette
  (`bg-gray-200`, `text-red-500`…), no inline color styles, no `.dark` variants.
- Red (`destructive` token) is reserved for failures. Status uses the status tokens
  (indexing, ready, failed).
- UI primitives come from shadcn/ui (Radix) in `src/components/ui/`; compose them, do not fork
  them. Merge classes with `cn()` from `@/lib/utils`. Adding a component is proposed to the user
  first (`npx shadcn add …`).
- API access only through the typed client generated from the OpenAPI schema
  (openapi-typescript + openapi-fetch); never call `fetch` with hand-written URLs in components.
  The base path is always the relative `/api` (Vite proxy in dev, nginx in the image); never an
  absolute URL or a per-environment host.
- Server state (documents list, indexing polling, chat) is isolated in hooks; components receive
  data and callbacks.
- Accessibility: semantic elements, labels for every input, visible focus, `aria-live` for
  streaming answers and indexing status.
- Citations render from the `sources` returned by the API; the UI never parses chunk IDs out of
  the answer text.
