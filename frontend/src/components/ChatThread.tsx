import { ArrowUpFromLine, Info } from 'lucide-react'

import { AnswerCard } from '@/components/AnswerCard'
import { ErrorCard } from '@/components/ErrorCard'
import { InsufficientEvidenceCard } from '@/components/InsufficientEvidenceCard'
import { LoadingCard } from '@/components/LoadingCard'
import { UploadButton } from '@/components/UploadButton'
import { Alert } from '@/components/ui/alert'
import type { ChatTurn } from '@/lib/chat'
import { ACCEPTED_FORMATS, formatCounts, type DocumentCounts } from '@/lib/documents'
import { cn } from '@/lib/utils'

interface ChatThreadProps {
  turns: readonly ChatTurn[]
  counts: DocumentCounts
  onUpload?: () => void
  onRetry?: (turn: ChatTurn) => void
  onRephrase?: (turn: ChatTurn) => void
  className?: string
}

export function ChatThread({ turns, counts, onUpload, onRetry, onRephrase, className }: ChatThreadProps) {
  const noDocuments = counts.ready + counts.indexing + counts.failed === 0

  if (noDocuments && turns.length === 0) {
    return <EmptyCollection onUpload={onUpload} className={className} />
  }

  return (
    <section aria-label="Conversation" className={cn('px-10 py-8', className)}>
      <div className="mx-auto flex max-w-205 flex-col gap-6">
        {counts.indexing > 0 && <IndexingBanner counts={counts} />}
        <div aria-live="polite" className="flex flex-col gap-6">
          {turns.map((turn, index) => (
            <div key={turn.id} className="flex flex-col gap-6">
              <QuestionBubble question={turn.question} />
              <TurnResult
                turn={turn}
                latest={index === turns.length - 1}
                onUpload={onUpload}
                onRetry={onRetry}
                onRephrase={onRephrase}
              />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function TurnResult({
  turn,
  latest,
  onUpload,
  onRetry,
  onRephrase,
}: {
  turn: ChatTurn
  latest: boolean
  onUpload?: () => void
  onRetry?: (turn: ChatTurn) => void
  onRephrase?: (turn: ChatTurn) => void
}) {
  switch (turn.status) {
    case 'loading':
      return <LoadingCard />
    case 'answered':
      return <AnswerCard answer={turn.answer} sources={turn.sources} compact={!latest} />
    case 'insufficient':
      return (
        <InsufficientEvidenceCard
          message={turn.message}
          relatedPassage={turn.relatedPassage}
          onRephrase={latest && onRephrase ? () => onRephrase(turn) : undefined}
          onUpload={latest ? onUpload : undefined}
        />
      )
    case 'error':
      return <ErrorCard message={turn.message} onRetry={onRetry ? () => onRetry(turn) : undefined} />
  }
}

function QuestionBubble({ question }: { question: string }) {
  return (
    <div className="flex max-w-4/5 flex-col items-end gap-1.5 self-end">
      <span className="text-caption font-semibold text-muted-foreground">You</span>
      <p className="m-0 rounded-2xl rounded-br-xs bg-bubble px-4 py-3 text-body leading-relaxed">
        {question}
      </p>
    </div>
  )
}

/** Handoff interaction 5: asking while indexing is allowed; only Ready documents are searched. */
function IndexingBanner({ counts }: { counts: DocumentCounts }) {
  const summary = formatCounts({ ...counts, failed: 0 })
  const detail =
    counts.ready > 0
      ? `You can already ask questions about the ${counts.ready} ready ${counts.ready === 1 ? 'document' : 'documents'}. The others will be included once they show Ready.`
      : 'You can ask questions once a document shows Ready.'

  return (
    <Alert variant="info" className="leading-normal">
      <Info aria-hidden="true" strokeWidth={1.75} />
      <span>
        <b>{summary}.</b> {detail}
      </span>
    </Alert>
  )
}

const STEPS = [
  { title: '1 · Upload', text: 'Add one or more documents.' },
  { title: '2 · Index', text: 'Wait for each file to show Ready.' },
  { title: '3 · Ask & verify', text: 'Check the excerpts under each answer.' },
]

function EmptyCollection({ onUpload, className }: { onUpload?: () => void; className?: string }) {
  return (
    <section
      aria-label="Conversation"
      className={cn('flex items-center justify-center px-10 py-16', className)}
    >
      <div className="flex w-full max-w-140 flex-col items-center gap-4 text-center">
        <span className="inline-flex size-16 items-center justify-center rounded-3xl bg-accent text-primary">
          <ArrowUpFromLine aria-hidden="true" strokeWidth={1.75} className="size-7.5" />
        </span>
        <h2 className="m-0 text-heading font-bold">Add documents to get started</h2>
        <p className="m-0 text-body leading-relaxed text-foreground-tertiary">
          Upload the documents you want to ask about. Once a document shows <b>Ready</b>, you can ask
          questions and check the excerpts each answer is based on.
        </p>
        <UploadButton size="lg" onClick={onUpload} />
        <p className="m-0 text-caption text-muted-foreground">{ACCEPTED_FORMATS}</p>
        <ol className="m-0 mt-6 grid w-full list-none grid-cols-1 gap-3 p-0 text-left sm:grid-cols-3">
          {STEPS.map((step) => (
            <li key={step.title} className="flex flex-col gap-1.5 rounded-xl border border-border p-4">
              <span className="text-caption font-bold text-primary">{step.title}</span>
              <span className="text-label text-foreground-tertiary">{step.text}</span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
