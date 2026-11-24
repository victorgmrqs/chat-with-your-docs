// View types for the chat thread, shaped after the API's ChatResponse (DOM-09, DOM-10, DOM-12).
import type { ChatResponse, PassageResponse, SourceResponse } from '@/api/client'

export interface Passage {
  chunkId: string
  documentId: string
  filename: string
  /** PDF page (1-based) or Markdown heading path; neither for plain text (DOM-05). */
  page: number | null
  heading: string | null
  passage: string
}

export interface Source extends Passage {
  /** The [n] marker in the answer text. */
  number: number
}

/** What a successful POST /chat turns into. */
export type TurnOutcome =
  | { status: 'answered'; answer: string; sources: Source[] }
  | { status: 'insufficient'; message: string; relatedPassage: Passage | null }

export type ChatTurn = { id: string; question: string } & (
  | { status: 'loading' }
  | TurnOutcome
  /** DOM-18: the question is kept; `retryable` turns on Retry (network and 5xx failures). */
  | { status: 'error'; message: string; retryable: boolean }
)

/** "Page 4", the heading path, or null when the format has no location (handoff A2). */
export function locationLabel(passage: Passage): string | null {
  if (passage.page !== null) return `Page ${passage.page}`
  return passage.heading
}

/** Document id → citation numbers, for highlighting cited documents in the sidebar. */
export function citedDocuments(sources: readonly Source[]): Record<string, number[]> {
  const cited: Record<string, number[]> = {}
  for (const source of sources) (cited[source.documentId] ??= []).push(source.number)
  return cited
}


function toPassage(response: PassageResponse): Passage {
  return {
    chunkId: response.chunk_id,
    documentId: response.document_id,
    filename: response.filename,
    page: response.page,
    heading: response.heading,
    passage: response.passage,
  }
}

function toSource(response: SourceResponse): Source {
  return { ...toPassage(response), number: response.number }
}

/** DOM-10: "insufficient_evidence" is a normal outcome with the backend's fixed message. */
export function toTurnOutcome(response: ChatResponse): TurnOutcome {
  if (response.outcome === 'answered') {
    return { status: 'answered', answer: response.answer, sources: response.sources.map(toSource) }
  }
  return {
    status: 'insufficient',
    message: response.answer,
    relatedPassage: response.related_passage ? toPassage(response.related_passage) : null,
  }
}
