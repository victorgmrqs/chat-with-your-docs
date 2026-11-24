> Part of the `testing-guide-cwyd-frontend` skill (see `../SKILL.md`).

# Mock health rules

- **Mock the network, not your code.** MSW is the only network double. Never `vi.mock` the
  API client, hooks or child components to make a test pass; never `vi.stubGlobal('fetch')`.
- **What `vi` is for:** timers (`vi.useFakeTimers`), `Date`, and browser APIs jsdom lacks
  (`matchMedia`, `ResizeObserver`, `scrollIntoView`) stubbed once in `src/test/setup.ts`.
- **Vitest 5 defaults:** `clearMocks` is on, so call history from setup files or `beforeAll` is
  gone before each test; `restoreMocks` restores only `vi.spyOn` spies. Restore real timers in
  `afterEach` explicitly.
- **Litmus test:** describe what the test proves without mentioning a double. "The failure
  message appears and Retry sends the question again" is behavior; "the client's `POST` was
  called with X" is wiring — assert what the user sees instead (counting requests is fine only
  when the count is the behavior, as in polling).
- **At most 3 doubles per test**, counting MSW overrides; more means the component does too
  much or the test belongs in Playwright.
