import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ChatTurn } from '@/lib/chat'

import { ChatThread } from './ChatThread'

const noDocuments = { ready: 0, indexing: 0, failed: 0 }
const someReady = { ready: 2, indexing: 0, failed: 0 }

describe('ChatThread', () => {
  it('shows the onboarding when the collection is empty', async () => {
    const onUpload = vi.fn()
    const user = userEvent.setup()
    render(<ChatThread turns={[]} counts={noDocuments} onUpload={onUpload} />)

    expect(screen.getByRole('heading', { name: 'Add documents to get started' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Upload documents' }))
    expect(onUpload).toHaveBeenCalledOnce()
  })

  it('invites an upload when every document failed and nothing was asked', () => {
    render(<ChatThread turns={[]} counts={{ ready: 0, indexing: 0, failed: 2 }} />)

    expect(screen.getByRole('heading', { name: 'Add documents to get started' })).toBeInTheDocument()
  })

  it('says only Ready documents are searched while others are indexing', () => {
    render(<ChatThread turns={[]} counts={{ ready: 2, indexing: 3, failed: 1 }} />)

    expect(screen.getByRole('status')).toHaveTextContent(
      '2 ready · 3 indexing. You can already ask questions about the 2 ready documents.',
    )
  })

  it('shows a loading card for a pending question', () => {
    const turns: ChatTurn[] = [{ id: '1', question: 'What is covered?', status: 'loading' }]
    render(<ChatThread turns={turns} counts={someReady} />)

    expect(screen.getByText('What is covered?')).toBeInTheDocument()
    expect(screen.getByRole('article', { name: 'Answer in progress' })).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByText('Searching your documents…')).toBeInTheDocument()
  })

  it('shows "not enough evidence" as a neutral outcome with an unnumbered related passage', async () => {
    const onRephrase = vi.fn()
    const turns: ChatTurn[] = [
      {
        id: '1',
        question: 'Parental leave for contractors?',
        status: 'insufficient',
        message: 'I couldn’t find enough evidence in the indexed documents to answer this question.',
        relatedPassage: {
          chunkId: 'c',
          documentId: 'd',
          filename: 'Employee_Handbook_2026.pdf',
          page: 31,
          heading: null,
          passage: 'Full-time employees are eligible for 16 weeks.',
        },
      },
    ]
    const user = userEvent.setup()
    render(<ChatThread turns={turns} counts={someReady} onRephrase={onRephrase} />)

    const card = screen.getByRole('article', { name: 'Not enough evidence' })
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(within(card).getByText('Employee_Handbook_2026.pdf')).toBeInTheDocument()
    expect(within(card).queryByRole('link')).not.toBeInTheDocument()
    await user.click(within(card).getByRole('button', { name: 'Rephrase the question' }))
    expect(onRephrase).toHaveBeenCalledWith(turns[0])
  })

  it('shows a request error as an alert with Retry', async () => {
    const onRetry = vi.fn()
    const turns: ChatTurn[] = [
      { id: '1', question: 'Q?', status: 'error', message: 'The request timed out.', retryable: true },
    ]
    const user = userEvent.setup()
    render(<ChatThread turns={turns} counts={someReady} onRetry={onRetry} />)

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent("Couldn't get an answer")
    expect(alert).toHaveTextContent('The request timed out.')
    await user.click(within(alert).getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledWith(turns[0])
  })

  it('shows earlier answers compact and the latest one in full', () => {
    const source = {
      number: 1,
      chunkId: 'c',
      documentId: 'd',
      filename: 'a.pdf',
      page: 1,
      heading: null,
      passage: 'Text.',
    }
    const turns: ChatTurn[] = [
      { id: '1', question: 'First?', status: 'answered', answer: 'One [1].', sources: [source] },
      { id: '2', question: 'Second?', status: 'answered', answer: 'Two [1].', sources: [source] },
    ]
    render(<ChatThread turns={turns} counts={someReady} />)

    expect(screen.getByRole('article', { name: 'Earlier answer' })).toHaveTextContent('One')
    expect(screen.getByRole('article', { name: 'Answer' })).toHaveTextContent('Two')
  })

  describe('scrolling to the latest turn', () => {
    const scrollIntoView = vi.fn()

    afterEach(() => {
      scrollIntoView.mockReset()
      // jsdom has no scrollIntoView; the stub only lives for these tests.
      delete (Element.prototype as Partial<Element>).scrollIntoView
    })

    it('scrolls when a question is sent and when its answer arrives, not on mount', () => {
      Element.prototype.scrollIntoView = scrollIntoView
      const first: ChatTurn = { id: '1', question: 'One?', status: 'answered', answer: 'One', sources: [] }
      const { rerender } = render(<ChatThread turns={[first]} counts={someReady} />)
      expect(scrollIntoView).not.toHaveBeenCalled()

      const asked: ChatTurn = { id: '2', question: 'Two?', status: 'loading' }
      rerender(<ChatThread turns={[first, asked]} counts={someReady} />)
      expect(scrollIntoView).toHaveBeenCalledTimes(1)

      const answered: ChatTurn = { ...asked, status: 'answered', answer: 'Two', sources: [] }
      rerender(<ChatThread turns={[first, answered]} counts={someReady} />)
      expect(scrollIntoView).toHaveBeenCalledTimes(2)
      expect(scrollIntoView).toHaveBeenLastCalledWith(expect.objectContaining({ block: 'start' }))
    })
  })
})
