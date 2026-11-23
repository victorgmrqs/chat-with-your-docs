// The screen against the API contract: MSW handlers (src/mocks) answer every request.
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import {
  documentResponse,
  domainError,
  insufficientResponse,
  MESSAGES,
  passageResponse,
} from '@/mocks/data'
import { mockDb } from '@/mocks/db'
import { documentsUnavailable } from '@/mocks/handlers/documents'
import { server } from '@/mocks/server'

import App from './App'

// DOM-19 polling, shortened: indexing ends only when a test calls mockDb.finishIndexing().
const POLL_MS = 40

function file(name: string, content = 'Some text.') {
  return new File([content], name, { type: 'application/octet-stream' })
}

function setup() {
  // applyAccept off: `accept` is only a hint to the picker; the API decides (DOM-01).
  const user = userEvent.setup({ applyAccept: false })
  mockDb.indexingMs = 60_000
  render(<App pollIntervalMs={POLL_MS} />)
  const input = () => screen.getByRole('textbox', { name: 'Your question' })
  const send = () => screen.getByRole('button', { name: 'Send' })
  const sidebar = () => screen.getByRole('complementary', { name: 'Documents' })
  return {
    user,
    sidebar,
    input,
    send,
    upload: (...files: File[]) =>
      user.upload(screen.getByLabelText('Choose documents to upload'), files),
    ask: async (question: string) => {
      await user.type(input(), question)
      await user.click(send())
    },
  }
}

/** One Ready document and, optionally, a POST /chat override; resolves once it is listed. */
async function setupWithReadyDocument(...chatHandlers: Parameters<typeof server.use>) {
  const document = documentResponse()
  mockDb.seed(document)
  server.use(...chatHandlers)
  const app = setup()
  await within(app.sidebar()).findByText('1 ready')
  return { ...app, document }
}

describe('App', () => {
  it('docs_chat_success: uploads two documents, asks, and shows the cited sources', async () => {
    const { sidebar, upload, ask } = setup()

    await upload(file('Employee_Handbook_2026.pdf'), file('Remote_Work_Policy.md'))
    expect(await within(sidebar()).findByText('0 ready · 2 indexing')).toBeInTheDocument()
    mockDb.finishIndexing()
    expect(await within(sidebar()).findByText('2 ready')).toBeInTheDocument()

    await ask('How many remote days are allowed?')

    const answer = await screen.findByRole('article', { name: 'Answer' })
    expect(within(answer).getByRole('heading', { name: 'Sources (2)' })).toBeInTheDocument()
    // File, location (page for a PDF, section for Markdown) and passage of each source
    // (parallel uploads: either may be source 1).
    for (const [filename, location] of [
      ['Employee_Handbook_2026.pdf', 'page 1'],
      ['Remote_Work_Policy.md', 'overview'],
    ]) {
      expect(within(answer).getByLabelText(new RegExp(`^Source [12]: ${filename}, ${location}$`))).toBeInTheDocument()
      expect(within(answer).getByText(`“An excerpt from ${filename}.”`)).toBeInTheDocument()
    }
    // Cited documents are highlighted in the sidebar.
    expect(within(sidebar()).getByText('Cited as source 1')).toBeInTheDocument()
    expect(within(sidebar()).getByText('Cited as source 2')).toBeInTheDocument()
  })

  it('docs_chat_no_ready_documents: Send stays unavailable while nothing is Ready', async () => {
    mockDb.seed(documentResponse({ filename: 'Travel_Expense_Policy.pdf', status: 'indexing' }))
    const { input, send } = setup()

    expect(await screen.findByText('Documents: 0 ready · 1 indexing')).toBeInTheDocument()
    expect(input()).toBeDisabled()
    expect(send()).toBeDisabled()
    expect(
      screen.getByText('Send is unavailable because no documents are ready yet. 1 document is still indexing.'),
    ).toBeInTheDocument()
  })

  it('docs_chat_insufficient_evidence: shows the neutral state without numbered citations', async () => {
    const { sidebar, ask } = await setupWithReadyDocument(
      http.post('/api/chat', () =>
        HttpResponse.json(insufficientResponse(passageResponse(documentResponse(), { passage: 'Parking rules.' }))),
      ),
    )

    await ask('What is the vacation policy?')

    const card = await screen.findByRole('article', { name: 'Not enough evidence' })
    expect(within(card).getByText(MESSAGES.insufficientEvidence)).toBeInTheDocument()
    expect(within(card).getByText(/Parking rules\./)).toBeInTheDocument()
    expect(screen.queryByRole('article', { name: 'Answer' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/^Source \d/)).not.toBeInTheDocument()
    expect(
      within(sidebar()).getByText('No document is highlighted: the latest answer cites no sources.'),
    ).toBeInTheDocument()
  })

  it('docs_chat_request_failure: keeps the question and retries a transient failure', async () => {
    const { user, ask } = await setupWithReadyDocument(
      http.post(
        '/api/chat',
        () => HttpResponse.json(domainError('chat_timeout', MESSAGES.chatTimeout), { status: 504 }),
        { once: true },
      ),
    )

    await ask('Who approves travel?')

    expect(await screen.findByText(MESSAGES.chatTimeout)).toBeInTheDocument()
    expect(screen.getByText('Who approves travel?')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Retry' }))

    expect(await screen.findByRole('article', { name: 'Answer' })).toBeInTheDocument()
    expect(screen.queryByText(MESSAGES.chatTimeout)).not.toBeInTheDocument()
    expect(screen.getAllByText('Who approves travel?')).toHaveLength(1)
  })

  it('docs_chat_request_failure: a rejected question shows the message without Retry', async () => {
    const { ask } = await setupWithReadyDocument(
      http.post('/api/chat', () =>
        HttpResponse.json(domainError('no_ready_documents', MESSAGES.noReadyDocuments), { status: 409 }),
      ),
    )

    await ask('Anything?')

    expect(await screen.findByText(MESSAGES.noReadyDocuments)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()
  })

  it('docs_chat_request_failure: a network failure is retryable', async () => {
    const { ask } = await setupWithReadyDocument(
      http.post('/api/chat', () => HttpResponse.error(), { once: true }),
    )

    await ask('Anything?')

    expect(await screen.findByText(/Couldn't reach the server/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })

  it('shows an upload rejection with the backend message', async () => {
    const { sidebar, upload } = setup()

    await upload(file('Q3_Notes.docx'))

    expect(await within(sidebar()).findByText("Q3_Notes.docx wasn't added")).toBeInTheDocument()
    expect(within(sidebar()).getByText(MESSAGES.unsupportedType('.docx'))).toBeInTheDocument()
    expect(within(sidebar()).getByText('No documents yet')).toBeInTheDocument()
  })

  it('retries an indexing_failed document by sending the same file again', async () => {
    const { user, sidebar, upload } = setup()

    await upload(file('Benefits_flaky.pdf'))
    await within(sidebar()).findByText('0 ready · 1 indexing')
    mockDb.finishIndexing()
    expect(await within(sidebar()).findByText(MESSAGES.indexingFailed)).toBeInTheDocument()

    await user.click(within(sidebar()).getByRole('button', { name: 'Retry' }))

    expect(await within(sidebar()).findByText('0 ready · 1 indexing')).toBeInTheDocument()
    mockDb.finishIndexing()
    expect(await within(sidebar()).findByText('1 ready')).toBeInTheDocument()
    expect(within(sidebar()).queryByText(MESSAGES.indexingFailed)).not.toBeInTheDocument()
  })

  it('shows the provider_misconfigured message and retries it once the operator fixed it', async () => {
    const { user, sidebar, upload } = setup()

    await upload(file('Benefits_misconfigured.pdf'))
    await within(sidebar()).findByText('0 ready · 1 indexing')
    mockDb.finishIndexing()
    expect(await within(sidebar()).findByText(MESSAGES.providerMisconfigured)).toBeInTheDocument()

    await user.click(within(sidebar()).getByRole('button', { name: 'Retry' }))

    expect(await within(sidebar()).findByText('0 ready · 1 indexing')).toBeInTheDocument()
    mockDb.finishIndexing()
    expect(await within(sidebar()).findByText('1 ready')).toBeInTheDocument()
  })

  it('does not claim an empty collection while the list is loading', async () => {
    // Held until the end of the test: a request left pending would stall the next test's.
    let answer = () => {}
    const answered = new Promise<void>((resolve) => (answer = resolve))
    server.use(
      http.get('/api/documents', async () => {
        await answered
        return HttpResponse.json([])
      }),
    )
    const { sidebar } = setup()

    expect(within(sidebar()).getByLabelText('Loading documents')).toHaveAttribute('aria-busy', 'true')
    expect(screen.queryByText('No documents yet')).not.toBeInTheDocument()
    expect(screen.queryByText('Add documents to get started')).not.toBeInTheDocument()
    expect(screen.queryByText(/^Documents: /)).not.toBeInTheDocument()

    answer()
    expect(await within(sidebar()).findByText('No documents yet')).toBeInTheDocument()
  })

  it('keeps an upload shown when an older list answers after it (DOM-19)', async () => {
    const existing = documentResponse({ filename: 'Existing_Policy.pdf' })
    mockDb.seed(existing)
    // The first list request is held until after the upload: it answers without the new file.
    let answer = () => {}
    const answered = new Promise<void>((resolve) => (answer = resolve))
    server.use(
      http.get(
        '/api/documents',
        async () => {
          await answered
          return HttpResponse.json([existing])
        },
        { once: true },
      ),
    )
    const { sidebar, upload } = setup()

    await upload(file('Remote_Work_Policy.md'))
    expect(await within(sidebar()).findByText('Remote_Work_Policy.md')).toBeInTheDocument()
    answer()

    // The stale list is fetched again: both documents, the upload still indexing.
    expect(await within(sidebar()).findByText('1 ready · 1 indexing')).toBeInTheDocument()
    expect(within(sidebar()).getByText('Existing_Policy.pdf')).toBeInTheDocument()
    expect(within(sidebar()).getByText('Remote_Work_Policy.md')).toBeInTheDocument()
  })

  it('shows a load failure with a retry', async () => {
    server.use(documentsUnavailable())
    const { user } = setup()

    expect(await screen.findByText("Couldn't load your documents")).toBeInTheDocument()
    // Not loaded is not empty: no empty-collection states under the error.
    expect(screen.getByText("Your documents couldn't be loaded.")).toBeInTheDocument()
    expect(screen.queryByText('No documents yet')).not.toBeInTheDocument()
    expect(screen.queryByText('Add documents to get started')).not.toBeInTheDocument()

    server.resetHandlers()
    await user.click(screen.getByRole('button', { name: 'Retry' }))

    expect(await screen.findByText('No documents yet')).toBeInTheDocument()
    expect(screen.queryByText("Couldn't load your documents")).not.toBeInTheDocument()
  })
})
