---
title: Strategic Suspense Boundaries
impact: HIGH
impactDescription: faster initial paint
tags: async, suspense, loading-states, layout-shift
---

## Strategic Suspense Boundaries

Instead of blocking the whole screen on a loading state until data arrives, use Suspense boundaries to show the wrapper UI immediately while only the data-dependent section waits. In this SPA, data comes from a client-side cache or loader that exposes a stable promise (never create the promise during render) and the component reads it with `use()`. `use()` and `<Suspense>` also cover `React.lazy` components. Requires a data layer that supports Suspense (for example router loaders or a query library with suspense mode); if none is in place, keep the loading branch local to the section instead.

**Incorrect (wrapper blocked by data fetching):**

```tsx
function Page() {
  const { data } = useChatHistory()
  if (!data) return <FullPageSpinner /> // Blocks entire page

  return (
    <div>
      <div>Sidebar</div>
      <div>Header</div>
      <div>
        <DataDisplay data={data} />
      </div>
      <div>Footer</div>
    </div>
  )
}
```

The entire layout waits for data even though only the middle section needs it.

**Correct (wrapper shows immediately, section suspends):**

```tsx
import { Suspense, use } from 'react'

function Page({ dataPromise }: { dataPromise: Promise<Data> }) {
  // dataPromise comes from a loader/cache, so it is stable across renders
  return (
    <div>
      <div>Sidebar</div>
      <div>Header</div>
      <div>
        <Suspense fallback={<Skeleton />}>
          <DataDisplay dataPromise={dataPromise} />
        </Suspense>
      </div>
      <div>Footer</div>
    </div>
  )
}

function DataDisplay({ dataPromise }: { dataPromise: Promise<Data> }) {
  const data = use(dataPromise) // Only suspends this component
  return <div>{data.content}</div>
}
```

Sidebar, Header, and Footer render immediately. Only DataDisplay waits for data.

**Sharing the promise across components:**

```tsx
function Page({ dataPromise }: { dataPromise: Promise<Data> }) {
  return (
    <div>
      <div>Sidebar</div>
      <div>Header</div>
      <Suspense fallback={<Skeleton />}>
        <DataDisplay dataPromise={dataPromise} />
        <DataSummary dataPromise={dataPromise} />
      </Suspense>
      <div>Footer</div>
    </div>
  )
}

function DataSummary({ dataPromise }: { dataPromise: Promise<Data> }) {
  const data = use(dataPromise) // Reuses the same promise
  return <div>{data.summary}</div>
}
```

Both components share the same promise, so only one fetch occurs. Layout renders immediately while both components wait together.

**When NOT to use this pattern:**

- Critical data needed for layout decisions (affects positioning)
- Small, fast queries where suspense overhead isn't worth it
- When you want to avoid layout shift (loading → content jump)

**Trade-off:** Faster initial paint vs potential layout shift. Choose based on your UX priorities.
