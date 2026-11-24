import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { InsufficientEvidenceCard } from './InsufficientEvidenceCard'

const message = "I couldn't find enough evidence in the indexed documents to answer this question."

describe('InsufficientEvidenceCard', () => {
  it('shows the related passage as non-evidence when one is returned', () => {
    render(
      <InsufficientEvidenceCard
        message={message}
        relatedPassage={{
          chunkId: 'c1',
          documentId: 'd1',
          filename: 'Remote_Work_Policy.pdf',
          page: 2,
          heading: null,
          passage: 'Employees may work remotely within their home country.',
        }}
      />,
    )

    expect(screen.getByRole('heading', { name: 'Not enough evidence' })).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Related passage · does not answer this question' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Remote_Work_Policy.pdf')).toBeInTheDocument()
  })

  it('shows "not enough evidence" without a related passage section when none is returned', () => {
    render(<InsufficientEvidenceCard message={message} relatedPassage={null} />)

    expect(screen.getByRole('article', { name: 'Not enough evidence' })).toHaveTextContent(message)
    expect(screen.queryByText(/Related passage/)).not.toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })
})
