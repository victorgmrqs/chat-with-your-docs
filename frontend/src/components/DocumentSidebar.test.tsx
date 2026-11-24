import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { DocumentItem } from '@/lib/documents'

import { DocumentSidebar } from './DocumentSidebar'

const ready: DocumentItem = { id: 'a', filename: 'Remote_Work_Policy.pdf', status: 'ready' }
const indexing: DocumentItem = { id: 'b', filename: 'Travel_Expense_Policy.pdf', status: 'indexing' }
const scanned: DocumentItem = {
  id: 'c',
  filename: 'Office_Floorplan_Scan.pdf',
  status: 'failed',
  failureMessage: 'No selectable text was found.',
  canRetry: false,
}
const transient: DocumentItem = {
  id: 'd',
  filename: 'Benefits_Overview_2026.pdf',
  status: 'failed',
  failureMessage: 'Indexing failed for a temporary reason.',
  canRetry: true,
}

function row(filename: string) {
  return screen.getByText(filename).closest('li') as HTMLElement
}

describe('DocumentSidebar', () => {
  it('shows the empty state and the accepted formats when there are no documents', () => {
    render(<DocumentSidebar documents={[]} />)

    expect(screen.getByText('No documents yet')).toBeInTheDocument()
    expect(screen.getByText('0 ready')).toBeInTheDocument()
    expect(screen.getByText('.pdf with selectable text, .md or .txt')).toBeInTheDocument()
  })

  it('lists each document with its status and the counts', () => {
    render(<DocumentSidebar documents={[ready, indexing, scanned]} />)

    expect(screen.getByText('1 ready · 1 indexing · 1 failed')).toBeInTheDocument()
    expect(within(row(ready.filename)).getByText('Ready')).toBeInTheDocument()
    expect(within(row(indexing.filename)).getByText('Indexing…')).toBeInTheDocument()
    expect(within(row(scanned.filename)).getByText('Failed')).toBeInTheDocument()
  })

  // CWYD-29: jsdom does no layout, so the "fits its column" half is the visual evidence in
  // docs/evidence/CWYD-29-sidebar.md (Playwright E2E, CWYD-8). This guards the other half: a long
  // name stays whole in the tooltip next to its status.
  it('keeps a long file name whole in its tooltip next to the status', () => {
    const long: DocumentItem = {
      id: 'e',
      filename: 'quarterly-employee-benefits-and-cafeteria-menu-overview-2026.txt',
      status: 'ready',
    }
    render(<DocumentSidebar documents={[long]} />)

    const name = screen.getByText(long.filename)
    expect(name).toHaveAttribute('title', long.filename)
    expect(within(row(long.filename)).getByText('Ready')).toBeInTheDocument()
  })

  it('offers another upload for a permanent failure', async () => {
    const onUpload = vi.fn()
    const onRemove = vi.fn()
    const user = userEvent.setup()
    render(<DocumentSidebar documents={[scanned]} onUpload={onUpload} onRetry={vi.fn()} onRemove={onRemove} />)

    const failed = row(scanned.filename)
    expect(within(failed).getByText('No selectable text was found.')).toBeInTheDocument()
    expect(within(failed).queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()
    await user.click(within(failed).getByRole('button', { name: 'Upload another file' }))
    await user.click(within(failed).getByRole('button', { name: 'Remove' }))

    expect(onUpload).toHaveBeenCalledOnce()
    expect(onRemove).toHaveBeenCalledWith(scanned)
  })

  it('offers Retry for a transient failure', async () => {
    const onRetry = vi.fn()
    const user = userEvent.setup()
    render(<DocumentSidebar documents={[transient]} onUpload={vi.fn()} onRetry={onRetry} />)

    await user.click(within(row(transient.filename)).getByRole('button', { name: 'Retry' }))

    expect(onRetry).toHaveBeenCalledWith(transient)
  })

  it('hides actions it has no callback for', () => {
    render(<DocumentSidebar documents={[transient]} />)

    expect(within(row(transient.filename)).queryByRole('button')).not.toBeInTheDocument()
  })

  it('highlights the documents cited by the latest answer', () => {
    render(<DocumentSidebar documents={[ready, indexing]} citations={{ a: [1, 3] }} />)

    expect(within(row(ready.filename)).getByText('Cited as source 1, 3')).toBeInTheDocument()
    expect(screen.getByText('Highlighted = cited in the latest answer')).toBeInTheDocument()
  })

  it('says nothing is highlighted when the latest answer cites no sources', () => {
    render(<DocumentSidebar documents={[ready]} citations={{}} />)

    expect(
      screen.getByText('No document is highlighted: the latest answer cites no sources.'),
    ).toBeInTheDocument()
  })

  it('shows an upload rejection as an alert', () => {
    render(
      <DocumentSidebar
        documents={[]}
        uploadRejection={{ filename: 'Q3_Notes.docx', message: '.docx is not supported.' }}
      />,
    )

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent("Q3_Notes.docx wasn't added")
    expect(alert).toHaveTextContent('.docx is not supported.')
  })
})
