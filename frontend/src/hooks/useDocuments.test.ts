// Real timers with a short interval: under faked setTimeout the MSW/undici request pipeline
// stalls after the first poll, so fake time would test the harness, not the hook.
import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { documentResponse } from '@/mocks/data'
import { mockDb } from '@/mocks/db'
import { documentsUnavailable } from '@/mocks/handlers/documents'
import { server } from '@/mocks/server'

import { useDocuments } from './useDocuments'

const INTERVAL_MS = 40

const pause = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

describe('useDocuments', () => {
  let listRequests = 0

  beforeEach(() => {
    listRequests = 0
    server.events.on('request:start', ({ request }) => {
      if (request.method === 'GET') listRequests += 1
    })
  })

  afterEach(() => {
    server.events.removeAllListeners()
  })

  it('polls while a document is indexing and stops once none is (DOM-19)', async () => {
    mockDb.indexingMs = 60_000
    mockDb.seed(documentResponse({ filename: 'Travel_Expense_Policy.pdf', status: 'indexing' }))

    const { result } = renderHook(() => useDocuments(INTERVAL_MS))

    await waitFor(() => expect(listRequests).toBeGreaterThanOrEqual(3))
    expect(result.current.documents[0].status).toBe('indexing')

    mockDb.finishIndexing()
    await waitFor(() => expect(result.current.documents[0].status).toBe('ready'))

    const afterReady = listRequests
    await pause(INTERVAL_MS * 5)
    expect(listRequests).toBe(afterReady)
  })

  it('does not poll when nothing is indexing', async () => {
    mockDb.seed(documentResponse({ status: 'ready' }))

    const { result } = renderHook(() => useDocuments(INTERVAL_MS))
    await waitFor(() => expect(result.current.documents).toHaveLength(1))
    await pause(INTERVAL_MS * 5)

    expect(listRequests).toBe(1)
  })

  it('keeps polling after a failed fetch while a document is indexing', async () => {
    mockDb.indexingMs = 60_000
    mockDb.seed(documentResponse({ status: 'indexing' }))
    const { result } = renderHook(() => useDocuments(INTERVAL_MS))
    await waitFor(() => expect(result.current.documents[0]?.status).toBe('indexing'))

    server.use(documentsUnavailable({ once: true }))

    await waitFor(() => expect(result.current.loadError).toBe('Database unavailable.'))
    mockDb.finishIndexing()
    await waitFor(() => expect(result.current.documents[0].status).toBe('ready'))
    expect(result.current.loadError).toBeNull()
  })
})
