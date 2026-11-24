// The only way the app reaches the API: a client typed from the OpenAPI schema (schema.d.ts is
// generated: `npm run api:types`). Paths have no /api prefix; the Vite proxy and nginx strip it.
import createClient from 'openapi-fetch'

import type { components, paths } from './schema'

export type DocumentResponse = components['schemas']['DocumentResponse']
export type ChatResponse = components['schemas']['ChatResponse']
export type PassageResponse = components['schemas']['PassageResponse']
export type SourceResponse = components['schemas']['SourceResponse']
export type DomainErrorResponse = components['schemas']['DomainErrorResponse']
export type ChatRequest = components['schemas']['ChatRequest']

export const api = createClient<paths>({
  // Same origin, /api path. Built from location.origin because fetch outside a browser
  // (Vitest) cannot resolve a relative URL; in the browser it is the same request.
  baseUrl: `${globalThis.location.origin}/api`,
})

const NETWORK_MESSAGE = "Couldn't reach the server. Check your connection and try again."
const UNEXPECTED_MESSAGE = 'Something went wrong on the server. Try again in a moment.'

/** A failed request: the backend's `detail` as message, or a network failure (status null). */
export class ApiError extends Error {
  readonly status: number | null

  constructor(status: number | null, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }

  /** DOM-18: network failures and 5xx may succeed if sent again; 4xx need a different request. */
  get transient(): boolean {
    return this.status === null || this.status >= 500
  }
}

function isDomainError(body: unknown): body is DomainErrorResponse {
  if (typeof body !== 'object' || body === null) return false
  const { code, detail } = body as Record<string, unknown>
  return typeof code === 'string' && typeof detail === 'string'
}

/**
 * Awaits an openapi-fetch call and returns its data, or throws ApiError. The message shown to
 * the user is the backend's own `detail` (DOM-16); anything else gets a generic message.
 */
export async function unwrap<T>(
  call: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  let result: Awaited<typeof call>
  try {
    result = await call
  } catch {
    throw new ApiError(null, NETWORK_MESSAGE)
  }
  const { data, error, response } = result
  if (response.ok && data !== undefined) return data
  if (isDomainError(error)) throw new ApiError(response.status, error.detail)
  throw new ApiError(response.status, UNEXPECTED_MESSAGE)
}

/** What to tell the user about any failure: an ApiError's message, never raw exception text. */
export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : UNEXPECTED_MESSAGE
}
