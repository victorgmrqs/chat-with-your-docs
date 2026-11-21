# Source

- Upstream repo: https://github.com/vercel-labs/agent-skills
- Path: `skills/react-best-practices` (upstream skill name `vercel-react-best-practices`)
- Commit: 5a37a6329fbad3666c3207392a6a7c0110e92efb
- License: MIT. The upstream repo has no LICENSE file; the license is declared in the upstream README and SKILL.md frontmatter. `LICENSE` in this folder is a standard MIT notice, "Copyright (c) Vercel, Inc." Originally created by @shuding at Vercel.
- Vendored: 2026-11-20
- Modified: yes

## Modifications

- Renamed to `react-spa-performance`; narrowed description; added "Project overrides"; removed `allowed-tools`-style extras and Next.js framing.
- SKILL.md index rewritten: 54 rules, 7 categories, renumbered.
- `_sections.md`: removed the Server-Side Performance section and renumbered.
- `bundle-dynamic-imports`, `bundle-preload`, `bundle-conditional`: `next/dynamic` replaced by `React.lazy` + `Suspense`; SSR / `typeof window` notes removed.
- `bundle-barrel-imports`, `bundle-analyzable-paths`: Next.js specifics removed, Vite-oriented.
- `async-dependencies`: `better-all` removed. `async-suspense-boundaries`: async server components replaced by `use()` with a stable promise.
- `client-event-listeners`: SWR removed (module-level registry). `client-localstorage-schema`: no dark mode example.
- `rerender-defer-reads`: `useSearchParams` from react-router noted. `rerender-use-ref-transient-values`, `rendering-hoist-jsx`, `js-batch-dom-css`: hardcoded colors replaced with tokens or removed.
- `rendering-activity`, `advanced-effect-event-deps`, `advanced-use-latest`: React 19.2 requirement noted. `rendering-usetransition-loading`: React 19 note.
- `rendering-resource-hints`: client-only rewrite. `rendering-svg-precision`: no `npx`. `js-cache-function-results`: example without auth cookie.

## Dropped files

16 rules: `async-api-routes`, `bundle-defer-third-party`, `client-swr-dedup`, `rendering-hydration-no-flicker`, `rendering-hydration-suppress-warning`, `rendering-script-defer-async`, and the 10 `server-*` rules. Also `AGENTS.md`, `README.md`, `metadata.json`, `rules/_template.md`.
