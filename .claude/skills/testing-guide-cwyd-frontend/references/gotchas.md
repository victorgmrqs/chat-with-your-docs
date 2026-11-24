> Part of the `testing-guide-cwyd-frontend` skill (see `../SKILL.md`).

# Gotchas

- **No auto cleanup with `globals: false`.** Testing Library registers `cleanup` only when it
  finds a global `afterEach`. `src/test/setup.ts` calls it explicitly; removing it makes the DOM
  of one test leak into the next (duplicate elements, "found multiple elements").
- **`defineConfig` must come from `vitest/config`** for the `test` block to typecheck; the one
  from `vite` rejects it (TS2769).
- **`getBy*` after a fetch fails intermittently.** React 19 commits the response in a later
  render; use `await screen.findBy*` or `await waitFor(...)`.
- **Unawaited async assertions fail in Vitest 5** (`expect(...).resolves` without `await`).
- **`act` comes from `react`.** `react-dom/test-utils` is gone in React 19; RTL 16 already wraps
  renders and events. Do not import `act` from the old path.
- **user-event and fake timers.** With `vi.useFakeTimers()`, create the user with
  `userEvent.setup({ advanceTimers: vi.advanceTimersByTime })` or interactions hang. Avoid
  `shouldAdvanceTime` (real time leaks in) and restore real timers in `afterEach`.
- **MSW 3 imports and option names.** Import from `msw/http`, `msw/node`, `msw/sse` (root
  exports are on their way out); the unhandled option is `onUnhandledFrame`, not
  `onUnhandledRequest`. MSW 3 is ESM-only and needs Node 22+ (the dev container runs Node 26).
- **Relative `/api` URLs in Node.** The app calls `/api/...`; Node's `fetch` needs an absolute
  URL. Build the client base URL from `window.location.origin` (jsdom provides one) and match
  handlers with `*/api/...`. Verify this when the client lands in CWYD-5.
- **Portals.** shadcn dialogs and popovers render outside the component root: query with
  `screen`, not with the `container` returned by `render`.
- **jsdom gaps.** No layout (`getBoundingClientRect` returns zeros), no `ResizeObserver`, no
  `matchMedia`, no `scrollIntoView`; stub them once in setup when a component needs them.
- **Vitest 5 output paths** moved under `.vitest/`; keep it gitignored if reports are enabled.
