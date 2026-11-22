import { ArrowRight } from 'lucide-react'
import { useId, useState, type FormEvent, type KeyboardEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

interface QuestionInputProps {
  readyCount: number
  indexingCount?: number
  isLoading?: boolean
  onSubmit?: (question: string) => void
  defaultValue?: string
  className?: string
}

function placeholderFor(readyCount: number, indexingCount: number, isLoading: boolean) {
  if (isLoading) return 'Wait for the current answer to finish…'
  if (readyCount > 0) return 'Ask about your documents…'
  return indexingCount > 0 ? 'Ask once a document is Ready' : 'Upload a document to start asking questions'
}

function hintFor(readyCount: number, indexingCount: number, isLoading: boolean) {
  if (isLoading) return 'Send is unavailable while the current answer loads.'
  if (readyCount > 0) return 'Answers include excerpts from your uploaded documents.'
  const stillIndexing =
    indexingCount > 0
      ? ` ${indexingCount} ${indexingCount === 1 ? 'document is' : 'documents are'} still indexing.`
      : ''
  return `Send is unavailable because no documents are ready yet.${stillIndexing}`
}

/** DOM-17: disabled with no Ready document and while an answer loads; the hint says why. */
export function QuestionInput({
  readyCount,
  indexingCount = 0,
  isLoading = false,
  onSubmit,
  defaultValue = '',
  className,
}: QuestionInputProps) {
  const [question, setQuestion] = useState(defaultValue)
  const inputId = useId()
  const hintId = useId()
  const disabled = readyCount === 0 || isLoading

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = question.trim()
    if (disabled || !text) return
    onSubmit?.(text)
    setQuestion('')
  }

  function submitOnEnter(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  return (
    <form
      aria-label="Ask a question"
      onSubmit={submit}
      className={cn('border-t border-border px-10 pt-4 pb-6', className)}
    >
      <div className="mx-auto flex max-w-205 flex-col gap-2">
        <label htmlFor={inputId} className="text-label font-semibold">
          Your question
        </label>
        <div className="flex items-stretch gap-3">
          <Textarea
            id={inputId}
            rows={2}
            value={question}
            disabled={disabled}
            placeholder={placeholderFor(readyCount, indexingCount, isLoading)}
            aria-describedby={hintId}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={submitOnEnter}
          />
          <Button type="submit" disabled={disabled} aria-describedby={hintId} className="h-auto min-w-26 px-4.5">
            Send
            {!disabled && <ArrowRight aria-hidden="true" strokeWidth={2.25} />}
          </Button>
        </div>
        <p id={hintId} className="m-0 text-caption text-muted-foreground">
          {hintFor(readyCount, indexingCount, isLoading)}
        </p>
      </div>
    </form>
  )
}
