import { http, HttpResponse } from 'msw'

import type { DocumentResponse, DomainErrorResponse } from '@/api/client'
import { ACCEPTED_EXTENSIONS } from '@/lib/documents'

import { domainError, extensionOf, MESSAGES } from '../data'
import { mockDb } from '../db'

const emptyFile = () =>
  HttpResponse.json<DomainErrorResponse>(domainError('empty_file', MESSAGES.emptyFile), { status: 400 })

export const documentHandlers = [
  http.get<never, never, DocumentResponse[]>('/api/documents', () =>
    HttpResponse.json(mockDb.list()),
  ),

  http.post<never, FormData, DocumentResponse | DomainErrorResponse>(
    '/api/documents',
    async ({ request }) => {
      const file = (await request.formData()).get('file')
      if (file === null || typeof file === 'string') return emptyFile()
      const extension = extensionOf(file.name)
      if (!(ACCEPTED_EXTENSIONS as readonly string[]).includes(extension)) {
        const shown = extension ? `.${extension}` : 'Files without an extension'
        return HttpResponse.json(domainError('unsupported_type', MESSAGES.unsupportedType(shown)), {
          status: 415,
        })
      }
      if (file.size === 0) return emptyFile()
      const { document, queued } = mockDb.upload(file.name, file.size)
      return HttpResponse.json(document, { status: queued ? 202 : 200 })
    },
  ),
]

/**
 * Override for tests: GET /documents fails with 503 (database unavailable), only for the next
 * request with `once`. Without it the failure holds until `server.resetHandlers()`, so a request
 * left over from an earlier test cannot use it up.
 */
export const documentsUnavailable = ({ once = false } = {}) =>
  http.get<never, never, DomainErrorResponse>(
    '/api/documents',
    () => HttpResponse.json(domainError('database_unavailable', 'Database unavailable.'), { status: 503 }),
    { once },
  )
