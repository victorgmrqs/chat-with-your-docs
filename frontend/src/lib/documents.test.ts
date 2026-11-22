import { describe, expect, it } from 'vitest'

import { formatCounts } from './documents'

describe('formatCounts', () => {
  it.each([
    [{ ready: 0, indexing: 0, failed: 0 }, '0 ready'],
    [{ ready: 5, indexing: 0, failed: 0 }, '5 ready'],
    [{ ready: 2, indexing: 3, failed: 1 }, '2 ready · 3 indexing · 1 failed'],
  ])('formats %o as "%s"', (counts, text) => {
    expect(formatCounts(counts)).toBe(text)
  })
})
