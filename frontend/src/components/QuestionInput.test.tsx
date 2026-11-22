import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { QuestionInput } from './QuestionInput'

describe('QuestionInput', () => {
  it('question_input_disabled: disables input and Send when no document is ready', () => {
    render(<QuestionInput readyCount={0} indexingCount={3} />)

    expect(screen.getByRole('textbox', { name: 'Your question' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    expect(
      screen.getByText(
        'Send is unavailable because no documents are ready yet. 3 documents are still indexing.',
      ),
    ).toBeInTheDocument()
  })

  it('question_input_disabled: disables input and Send while an answer is loading', () => {
    render(<QuestionInput readyCount={2} isLoading />)

    expect(screen.getByRole('textbox', { name: 'Your question' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    expect(screen.getByPlaceholderText('Wait for the current answer to finish…')).toBeInTheDocument()
    expect(screen.getByText('Send is unavailable while the current answer loads.')).toBeInTheDocument()
  })

  it('asks the user to upload when there are no documents at all', () => {
    render(<QuestionInput readyCount={0} />)

    expect(screen.getByPlaceholderText('Upload a document to start asking questions')).toBeInTheDocument()
    expect(screen.getByText('Send is unavailable because no documents are ready yet.')).toBeInTheDocument()
  })

  it('submits the trimmed question and clears the input', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<QuestionInput readyCount={1} onSubmit={onSubmit} />)

    const input = screen.getByRole('textbox', { name: 'Your question' })
    await user.type(input, '  What is the monthly limit?  ')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(onSubmit).toHaveBeenCalledWith('What is the monthly limit?')
    expect(input).toHaveValue('')
  })

  it('submits with Enter and keeps Shift+Enter for a new line', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<QuestionInput readyCount={1} onSubmit={onSubmit} />)

    const input = screen.getByRole('textbox', { name: 'Your question' })
    await user.type(input, 'First line{Shift>}{Enter}{/Shift}second line{Enter}')

    expect(onSubmit).toHaveBeenCalledWith('First line\nsecond line')
  })

  it('ignores an empty question', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<QuestionInput readyCount={1} onSubmit={onSubmit} />)

    await user.type(screen.getByRole('textbox', { name: 'Your question' }), '   ')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(onSubmit).not.toHaveBeenCalled()
  })
})
