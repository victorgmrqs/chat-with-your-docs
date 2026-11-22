// View types for the document sidebar, shaped after the API's DocumentResponse (DOM-02, DOM-03).
export type DocumentStatus = 'indexing' | 'ready' | 'failed'

export interface DocumentItem {
  id: string
  filename: string
  status: DocumentStatus
  /** Backend message for a failed document (DOM-03); shown as is. */
  failureMessage?: string | null
  /** True for transient failures: uploading the same file again indexes it (DOM-04). */
  canRetry?: boolean
}

export interface DocumentCounts {
  ready: number
  indexing: number
  failed: number
}

/** DOM-16: the formats accepted by DOM-01, in user-facing words. */
export const ACCEPTED_FORMATS = '.pdf with selectable text, .md or .txt'

export function countDocuments(documents: readonly DocumentItem[]): DocumentCounts {
  const counts: DocumentCounts = { ready: 0, indexing: 0, failed: 0 }
  for (const document of documents) counts[document.status] += 1
  return counts
}

/** "2 ready · 3 indexing · 1 failed"; zero indexing or failed is left out, ready never is. */
export function formatCounts(counts: DocumentCounts): string {
  return [
    `${counts.ready} ready`,
    counts.indexing > 0 && `${counts.indexing} indexing`,
    counts.failed > 0 && `${counts.failed} failed`,
  ]
    .filter(Boolean)
    .join(' · ')
}
