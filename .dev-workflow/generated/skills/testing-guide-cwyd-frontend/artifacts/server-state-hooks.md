> Part of the `testing-guide-cwyd-frontend` skill (see `../SKILL.md`).

# Server-state hooks (`src/**/use*.ts`)

## What to test
- Polling: indexing status is polled until a terminal state (`ready`/`failed`), then stops;
  the interval is respected; unmount stops polling.
- Error mapping: API error codes → messages or states the UI shows.
- Mutations: after upload or delete, the list reflects the change (refetch or cache update).

## Layer assignment
- **Through the component that uses the hook** by default: the component test already proves
  the hook's behavior as the user sees it.
- **`renderHook` test** only for logic that is hard to reach through UI: polling cadence and
  stop conditions, cancellation on unmount.
- Network always through MSW; never mock the client inside the hook.

## Setup pattern
```ts
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw/http'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

it('stops polling once the document is ready', async () => {
  const statuses = ['indexing', 'indexing', 'ready']
  let calls = 0
  server.use(http.get('*/api/documents/d1', () =>
    HttpResponse.json({ id: 'd1', status: statuses[calls++] ?? 'ready' })))
  const { result } = renderHook(() => useDocumentStatus('d1', { intervalMs: 1000 }))
  await vi.advanceTimersByTimeAsync(3000)
  await waitFor(() => expect(result.current.status).toBe('ready'))
  await vi.advanceTimersByTimeAsync(5000)
  expect(calls).toBe(3)
})
```
- When the test also clicks or types, create the user with
  `userEvent.setup({ advanceTimers: vi.advanceTimersByTime })`.
- Counting requests in a handler is acceptable here because the number of requests is the
  behavior (polling stops).

## When to skip
- Hooks that only wrap one request without logic: covered by the component test.

## Examples from project
- None yet. First ones: document list and indexing status (CWYD-10/CWYD-5).
