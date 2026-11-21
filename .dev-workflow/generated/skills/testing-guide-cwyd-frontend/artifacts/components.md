> Part of the `testing-guide-cwyd-frontend` skill (see `../SKILL.md`).

# Components (`src/**/*.tsx`, excluding `src/components/ui/`)

## What to test
- Each state the component renders: loading, empty, error, success. For this product that
  includes failed upload, indexing failed, "not enough evidence" and citations.
- The main interactions and their visible outcome (submit question → answer appears; retry →
  request repeated; delete → item disappears).
- Accessibility contracts the user relies on: headings, labelled inputs, `aria-live` regions.
- Red (destructive token) only on failure states — assert the failure message is present, not
  the color.

## Layer assignment
- **Component test** (Vitest + jsdom + Testing Library) with MSW serving the API.
- A presentational component without states or interactions: no dedicated test; it is covered
  by its parent's test.
- Journeys that cross pages and need the real backend: Playwright (`artifacts/e2e-flows.md`).

## Setup pattern
```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw/http'
import { describe, expect, it } from 'vitest'
import { server } from '../test/server'
import { DocumentList } from './DocumentList'

describe('DocumentList', () => {
  it('shows the failure reason when indexing failed', async () => {
    server.use(
      http.get('*/api/documents', () =>
        HttpResponse.json([{ id: 'd1', filename: 'a.pdf', status: 'failed', reason: 'Unreadable PDF' }]),
      ),
    )
    render(<DocumentList />)
    expect(await screen.findByText('Unreadable PDF')).toBeInTheDocument()
  })

  it('asks again after a failure', async () => {
    const user = userEvent.setup()
    render(<DocumentList />)
    await user.click(await screen.findByRole('button', { name: 'Retry' }))
    // assert the visible result, not the call
  })
})
```
- Default handlers (happy path) are registered in the shared server; each test overrides only
  what it needs with `server.use(...)`.

## When to skip
- Markup-only components, layout wrappers, icon buttons without logic.
- Styling, tokens and spacing (design review, not tests).

## Examples from project
- `App` — placeholder without state → one smoke test asserting the page heading
  (`src/App.test.tsx`). It is replaced by real screens in CWYD-10.
