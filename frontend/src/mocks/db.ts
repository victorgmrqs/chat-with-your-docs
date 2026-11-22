// In-memory stand-in for the backend's document state, shared by the default handlers.
// Indexing is simulated by time: a document uploaded now becomes `ready` after `indexingMs`.
// Browser demo triggers (VITE_API_MOCKS=true): a filename containing "scanned" fails with
// no_extractable_text; one containing "flaky" fails with indexing_failed on its first upload.
import type { DocumentResponse } from '@/api/client'

import { documentResponse, extensionOf, MESSAGES } from './data'

type Outcome = 'ready' | 'no_extractable_text' | 'indexing_failed'

const FAILURE_MESSAGE: Record<Exclude<Outcome, 'ready'>, string> = {
  no_extractable_text: MESSAGES.noExtractableText,
  indexing_failed: MESSAGES.indexingFailed,
}

/** First upload of a file: the demo triggers in its name decide how indexing ends. */
function outcomeFor(filename: string): Outcome {
  if (filename.includes('scanned')) return 'no_extractable_text'
  if (filename.includes('flaky')) return 'indexing_failed'
  return 'ready'
}

interface StoredDocument {
  document: DocumentResponse
  /** Epoch ms when indexing ends; only read while the document is `indexing`. */
  finishesAt: number
  outcome: Outcome
}

const DEFAULT_INDEXING_MS = 1500

let stored: StoredDocument[] = []
/** Questions that already got their one simulated timeout (handlers/chat.ts). */
const timedOut = new Set<string>()

export const mockDb = {
  indexingMs: DEFAULT_INDEXING_MS,

  reset() {
    stored = []
    timedOut.clear()
    this.indexingMs = DEFAULT_INDEXING_MS
  },

  /** Documents as the API would return them now, newest first. */
  list(): DocumentResponse[] {
    const now = Date.now()
    for (const entry of stored) {
      if (entry.document.status === 'indexing' && now >= entry.finishesAt) finish(entry)
    }
    return stored.map((entry) => entry.document)
  },

  /** Puts documents in their given state, e.g. already `ready`. */
  seed(...documents: DocumentResponse[]) {
    for (const document of documents) {
      stored.unshift({ document, finishesAt: Date.now() + this.indexingMs, outcome: 'ready' })
    }
  },

  /** True the first time a question is seen, so a retry of the same question succeeds. */
  firstAttempt(question: string): boolean {
    if (timedOut.has(question)) return false
    timedOut.add(question)
    return true
  },

  /** Ends indexing now for every `indexing` document (tests that must not depend on time). */
  finishIndexing() {
    for (const entry of stored) entry.finishesAt = 0
  },

  /** POST /documents semantics (DOM-04): returns the document and whether it was (re)queued. */
  upload(filename: string, size: number): { document: DocumentResponse; queued: boolean } {
    const existing = stored.find(
      (entry) => entry.document.filename === filename && entry.document.size_bytes === size,
    )
    if (existing && existing.document.failure_reason !== 'indexing_failed') {
      return { document: existing.document, queued: false }
    }
    // A transient failure succeeds on the second upload.
    const outcome = existing ? 'ready' : outcomeFor(filename)
    const document = documentResponse({
      ...(existing && { id: existing.document.id }), // DOM-04: same document, indexed again
      filename,
      size_bytes: size,
      format: extensionOf(filename) as DocumentResponse['format'],
      status: 'indexing',
      chunk_count: 0,
    })
    const entry = { document, finishesAt: Date.now() + this.indexingMs, outcome }
    stored = [entry, ...stored.filter((item) => item !== existing)]
    return { document, queued: true }
  },
}

function finish(entry: StoredDocument) {
  const updated_at = new Date().toISOString()
  entry.document =
    entry.outcome === 'ready'
      ? { ...entry.document, status: 'ready', chunk_count: 8, updated_at }
      : {
          ...entry.document,
          status: 'failed',
          failure_reason: entry.outcome,
          failure_message: FAILURE_MESSAGE[entry.outcome],
          updated_at,
        }
}
