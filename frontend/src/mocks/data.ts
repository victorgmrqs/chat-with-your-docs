// Typed API payload builders for MSW handlers and tests. Messages are the backend's own
// (backend/app/domain), so mocked screens read like the real ones.
import type {
  ChatResponse,
  DocumentResponse,
  DomainErrorResponse,
  PassageResponse,
  SourceResponse,
} from '@/api/client'

export const MESSAGES = {
  noExtractableText:
    'No selectable text was found (for example a scanned PDF). Upload another version with selectable text.',
  indexingFailed: 'Indexing failed for a temporary reason. Upload the same file again to retry.',
  providerMisconfigured:
    'The embeddings provider rejected the configured API key or model. Ask the operator to check OPENAI_API_KEY and EMBEDDING_MODEL, then upload the same file again.',
  unsupportedType: (extension: string) =>
    `${extension} is not supported. Upload a .pdf with selectable text, a .md or a .txt file.`,
  emptyFile: 'The file is empty. Upload a .pdf with selectable text, a .md or a .txt file.',
  emptyQuestion: 'The question is empty. Type a question about your documents.',
  noReadyDocuments: 'No document is ready yet. Upload a document and wait until it is Ready.',
  insufficientEvidence:
    'Not enough evidence in your documents to answer this question. Rephrase the question or upload a document that covers it.',
  chatTimeout: 'The answer took too long. Your question was kept: try again.',
  // nginx's own body (frontend/nginx/default.conf.template, DOM-27), not the API's.
  rateLimited: 'Too many requests. Try again in a minute.',
} as const

/** Lower-cased extension without the dot; '' when the name has none. */
export function extensionOf(filename: string): string {
  const dot = filename.lastIndexOf('.')
  return dot === -1 ? '' : filename.slice(dot + 1).toLowerCase()
}

export function domainError(code: string, detail: string): DomainErrorResponse {
  return { code, detail, request_id: crypto.randomUUID() }
}

export function documentResponse(overrides: Partial<DocumentResponse> = {}): DocumentResponse {
  const now = new Date().toISOString()
  return {
    id: crypto.randomUUID(),
    filename: 'Employee_Handbook_2026.pdf',
    format: 'pdf',
    size_bytes: 1024,
    status: 'ready',
    failure_reason: null,
    failure_message: null,
    can_retry: false,
    chunk_count: 12,
    created_at: now,
    updated_at: now,
    ...overrides,
  }
}

export function passageResponse(
  document: Pick<DocumentResponse, 'id' | 'filename'>,
  overrides: Partial<PassageResponse> = {},
): PassageResponse {
  return {
    chunk_id: crypto.randomUUID(),
    document_id: document.id,
    filename: document.filename,
    page: 1,
    heading: null,
    passage: `An excerpt from ${document.filename}.`,
    ...overrides,
  }
}

export function sourceResponse(
  document: Pick<DocumentResponse, 'id' | 'filename'>,
  number: number,
  overrides: Partial<SourceResponse> = {},
): SourceResponse {
  return { ...passageResponse(document), number, ...overrides }
}

function chatResponse(overrides: Pick<ChatResponse, 'outcome' | 'answer'> & Partial<ChatResponse>): ChatResponse {
  return {
    request_id: crypto.randomUUID(),
    sources: [],
    related_passage: null,
    provider: 'fake',
    model: 'fake-model',
    reranked: false,
    ...overrides,
  }
}

export function answeredResponse(sources: SourceResponse[], answer?: string): ChatResponse {
  return chatResponse({
    outcome: 'answered',
    answer:
      answer ??
      sources.map((source) => `${source.filename} covers it [${source.number}].`).join(' '),
    sources,
  })
}

export function insufficientResponse(related: PassageResponse | null = null): ChatResponse {
  return chatResponse({
    outcome: 'insufficient_evidence',
    answer: MESSAGES.insufficientEvidence,
    related_passage: related,
  })
}
