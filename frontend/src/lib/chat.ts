// View types for the chat thread, shaped after the API's ChatResponse (DOM-09, DOM-10, DOM-12).
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

export type ChatTurn = { id: string; question: string } & (
  | { status: 'loading' }
  | { status: 'answered'; answer: string; sources: Source[] }
  | { status: 'insufficient'; message: string; relatedPassage: Passage | null }
  | { status: 'error'; message: string }
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
