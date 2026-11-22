import { useCallback, useEffect, useRef, useState } from 'react'

import { api, errorMessage, unwrap, type DocumentResponse } from '@/api/client'
import { toDocumentItem, type DocumentItem } from '@/lib/documents'

/** DOM-19: how often the list is fetched again while a document is indexing. */
export const POLL_INTERVAL_MS = 2000

/** `loading` and `unavailable`: the collection is unknown, not empty (no first answer yet). */
export type ListState = 'loading' | 'unavailable' | 'loaded'

/** Same rows in the same states: keeps the previous array, so a quiet poll re-renders nothing. */
function sameItems(a: readonly DocumentItem[], b: readonly DocumentItem[]) {
  return (
    a.length === b.length &&
    a.every(
      (item, index) =>
        item.id === b[index].id &&
        item.status === b[index].status &&
        item.failureMessage === b[index].failureMessage,
    )
  )
}

/**
 * The owner's documents as the API reports them (DOM-19): loaded on mount and fetched again
 * every `pollIntervalMs` while any document is `indexing`; polling stops when none is.
 */
export function useDocuments(pollIntervalMs = POLL_INTERVAL_MS) {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)
  // Bumped after every fetch, so a failed fetch still schedules the next poll.
  const [fetches, setFetches] = useState(0)
  // A list fetched before the latest local change (an upload) is stale and is dropped.
  const changes = useRef(0)

  // Written with .then callbacks: state is only set after the response, never during the effect.
  // Each callback sets all its state at once, so a poll renders once.
  const refresh = useCallback(() => {
    const load = (): Promise<void> => {
      const startedAt = changes.current
      return unwrap(api.GET('/documents')).then(
        (data) => {
          // DOM-19: older than an upload shown since; it could drop that upload, so fetch again.
          if (startedAt !== changes.current) return load()
          const next = data.map(toDocumentItem)
          setDocuments((current) => (sameItems(current, next) ? current : next))
          setLoaded(true)
          setLoadError(null)
          setFetches((count) => count + 1)
        },
        (error: unknown) => {
          setLoadError(errorMessage(error))
          setFetches((count) => count + 1)
        },
      )
    }
    return load()
  }, [])

  /** Shows an upload's result right away; polling picks up its later states. */
  const upsert = useCallback((response: DocumentResponse) => {
    changes.current += 1
    const item = toDocumentItem(response)
    setDocuments((current) => [item, ...current.filter((document) => document.id !== item.id)])
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const indexing = documents.some((document) => document.status === 'indexing')
  useEffect(() => {
    if (!indexing) return
    const timer = setTimeout(() => void refresh(), pollIntervalMs)
    return () => clearTimeout(timer)
  }, [indexing, fetches, refresh, pollIntervalMs])

  const listState: ListState = loaded ? 'loaded' : loadError ? 'unavailable' : 'loading'

  return { documents, listState, loadError, refresh, upsert }
}
