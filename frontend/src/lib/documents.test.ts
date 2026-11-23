import { describe, expect, it } from 'vitest'

import { documentResponse, MESSAGES } from '@/mocks/data'

import { formatCounts, toDocumentItem } from './documents'

describe('formatCounts', () => {
  it.each([
    [{ ready: 0, indexing: 0, failed: 0 }, '0 ready'],
    [{ ready: 5, indexing: 0, failed: 0 }, '5 ready'],
    [{ ready: 2, indexing: 3, failed: 1 }, '2 ready · 3 indexing · 1 failed'],
  ])('formats %o as "%s"', (counts, text) => {
    expect(formatCounts(counts)).toBe(text)
  })
})

describe('toDocumentItem', () => {
  it("offers Retry as the backend's can_retry says (DOM-04, DOM-25)", () => {
    const failed = (can_retry: boolean) =>
      toDocumentItem(
        documentResponse({ status: 'failed', failure_reason: 'indexing_failed', failure_message: MESSAGES.indexingFailed, can_retry }),
      )

    expect(failed(true)).toMatchObject({ status: 'failed', canRetry: true, failureMessage: MESSAGES.indexingFailed })
    expect(failed(false).canRetry).toBe(false)
  })
})
