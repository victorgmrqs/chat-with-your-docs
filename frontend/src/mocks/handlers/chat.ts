import { http, HttpResponse } from 'msw'

import type {
  ChatRequest,
  ChatResponse,
  DocumentResponse,
  DomainErrorResponse,
  PassageResponse,
} from '@/api/client'

import {
  answeredResponse,
  domainError,
  insufficientResponse,
  MESSAGES,
  passageResponse,
  sourceResponse,
} from '../data'
import { mockDb } from '../db'

/** DOM-05: a page for PDFs, a heading path for Markdown, no location for plain text. */
function locationOf(document: DocumentResponse): Pick<PassageResponse, 'page' | 'heading'> {
  if (document.format === 'pdf') return { page: 1, heading: null }
  if (document.format === 'md') return { page: null, heading: 'Overview' }
  return { page: null, heading: null }
}

/**
 * Answers from the Ready documents, citing up to two of them. Browser demo triggers
 * (VITE_API_MOCKS=true): a question containing "unknown" gets insufficient evidence; one
 * containing "timeout" gets a 504 on its first attempt only, so Retry answers it (DOM-18).
 */
export const chatHandlers = [
  http.post<never, ChatRequest, ChatResponse | DomainErrorResponse>(
    '/api/chat',
    async ({ request }) => {
      const question = (await request.json()).question.trim()
      if (!question) {
        return HttpResponse.json(domainError('empty_question', MESSAGES.emptyQuestion), {
          status: 400,
        })
      }
      const ready = mockDb.list().filter((document) => document.status === 'ready')
      if (ready.length === 0) {
        return HttpResponse.json(domainError('no_ready_documents', MESSAGES.noReadyDocuments), {
          status: 409,
        })
      }
      if (question.includes('timeout') && mockDb.firstAttempt(question)) {
        return HttpResponse.json(domainError('chat_timeout', MESSAGES.chatTimeout), { status: 504 })
      }
      if (question.includes('unknown')) {
        return HttpResponse.json(insufficientResponse(passageResponse(ready[0], locationOf(ready[0]))))
      }
      return HttpResponse.json(
        answeredResponse(
          ready.slice(0, 2).map((document, index) => sourceResponse(document, index + 1, locationOf(document))),
        ),
      )
    },
  ),
]
