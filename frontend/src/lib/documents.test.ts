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
  it('offers Retry only for a transient indexing failure (DOM-03, DOM-04)', () => {
    const failed = (failure_reason: 'indexing_failed' | 'no_extractable_text') =>
      toDocumentItem(documentResponse({ status: 'failed', failure_reason, failure_message: MESSAGES.indexingFailed }))

    expect(failed('indexing_failed')).toMatchObject({ status: 'failed', canRetry: true, failureMessage: MESSAGES.indexingFailed })
    expect(failed('no_extractable_text').canRetry).toBe(false)
  })
})
