import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { Source } from '@/lib/chat'

import { AnswerCard } from './AnswerCard'

const sources: Source[] = [
  {
    number: 1,
    chunkId: 'c1',
    documentId: 'd1',
    filename: 'Remote_Work_Policy.pdf',
    page: 4,
    heading: null,
    passage: 'Remote employees may use a coworking space with manager approval.',
  },
  {
    number: 2,
    chunkId: 'c2',
    documentId: 'd2',
    filename: 'Onboarding.md',
    page: null,
    heading: 'Equipment > Laptops',
    passage: 'Every employee receives a laptop.',
  },
]

describe('AnswerCard', () => {
  it('links each citation number to its source card', () => {
    render(<AnswerCard answer="Approval is required [1]. Laptops are provided [2]." sources={sources} />)

    const citation = screen.getByRole('link', { name: 'Source 1: Remote_Work_Policy.pdf, page 4' })
    const target = document.getElementById(citation.getAttribute('href')!.slice(1))
    expect(target).toHaveTextContent('Remote_Work_Policy.pdf')
    expect(screen.getByRole('link', { name: 'Source 2: Onboarding.md, equipment > laptops' })).toBeInTheDocument()
  })

  it('lists the sources with page or heading and passage', () => {
    render(<AnswerCard answer="Approval is required [1]." sources={sources} />)

    expect(screen.getByRole('heading', { level: 2, name: 'Answer' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 3, name: 'Sources (2)' })).toBeInTheDocument()
    const list = screen.getByRole('list')
    expect(within(list).getByText('Page 4')).toBeInTheDocument()
    expect(within(list).getByText('Equipment > Laptops')).toBeInTheDocument()
    expect(within(list).getByText('“Every employee receives a laptop.”')).toBeInTheDocument()
  })

  it('leaves a marker without a matching source as plain text', () => {
    render(<AnswerCard answer="See note [7]." sources={sources} />)

    expect(screen.getByText(/See note \[7\]\./)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Source 7/ })).not.toBeInTheDocument()
  })

  it('keeps the sources of an earlier answer collapsed until asked', async () => {
    const user = userEvent.setup()
    render(<AnswerCard answer="Approval is required [1]." sources={sources} compact />)

    const toggle = screen.getByRole('button', {
      name: 'Show 2 sources · Remote_Work_Policy.pdf, Onboarding.md',
    })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('Page 4')).not.toBeInTheDocument()

    await user.click(toggle)

    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Page 4')).toBeInTheDocument()
  })
})
