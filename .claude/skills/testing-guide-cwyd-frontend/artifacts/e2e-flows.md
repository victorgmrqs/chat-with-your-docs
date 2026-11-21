> Part of the `testing-guide-cwyd-frontend` skill (see `../SKILL.md`).

# Browser flows (`frontend/e2e/**`, Playwright)

## What to test
- A handful of critical journeys on the real stack:
  1. Upload a fixture document → status reaches Ready.
  2. Ask a question answered by that document → answer with at least one citation that opens
     the source.
  3. Ask a question the documents cannot answer → explicit "not enough evidence".
  4. Upload an unsupported file → visible failure, nothing indexed.
- That the built bundle and the nginx `/api` proxy work together (implicitly, by every journey).

## Layer assignment
- **E2E only**, headless by default, driven through the Playwright CLI (`playwright-cli` skill),
  against `docker compose up --build --wait`.
- Component states and edge cases stay in Vitest; E2E does not repeat them.
- LLM in E2E: the Compose stack runs with real providers only when a human runs the suite
  with keys; the default run uses the backend's fake provider configuration once it exists
  (decided in CWYD-8). Never commit keys or recorded auth state.

## Setup pattern
```ts
import { expect, test } from '@playwright/test'

test('answers with a citation from an uploaded document', async ({ page }) => {
  await page.goto('/')                                 // baseURL from env, e.g. http://localhost:8080
  await page.getByLabel('Upload document').setInputFiles('e2e/fixtures/expense-policy.md')
  await expect(page.getByText('Ready')).toBeVisible({ timeout: 60_000 })
  await page.getByRole('textbox', { name: 'Question' }).fill('What is the expense limit?')
  await page.getByRole('button', { name: 'Ask' }).click()
  await expect(page.getByRole('link', { name: /expense-policy\.md/ })).toBeVisible()
})
```
- Use web-first assertions (`expect(locator).toBeVisible()`), which retry; never fixed waits.
- Isolate data per test (unique filenames or a fresh owner) so runs can repeat on the same stack.

## When to skip
- Anything a component test already proves (validation messages, empty states, layout).

## Examples from project
- None yet. Playwright is installed and configured in CWYD-8.
