import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { Source } from '@/lib/chat'

import { SourceCard } from './SourceCard'

const source: Source = {
  number: 1,
  chunkId: 'c1',
  documentId: 'd1',
  filename: 'notes.txt',
  page: null,
  heading: null,
  passage: 'A long passage. '.repeat(20),
}

describe('SourceCard', () => {
  it('expands a long passage on request', async () => {
    const user = userEvent.setup()
    render(<SourceCard source={source} />)

    const toggle = screen.getByRole('button', { name: 'Show full passage' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')

    await user.click(toggle)

    expect(screen.getByRole('button', { name: 'Show less' })).toHaveAttribute('aria-expanded', 'true')
  })

  it('shows no location and no toggle for a short plain-text passage', () => {
    render(<SourceCard source={{ ...source, passage: 'Short.' }} />)

    expect(screen.queryByText(/^Page/)).not.toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
