import { AppLayout } from '@/components/AppLayout'
import { ChatHeader } from '@/components/ChatHeader'
import { ChatThread } from '@/components/ChatThread'
import { DocumentRow, DocumentSidebar } from '@/components/DocumentSidebar'
import { ErrorCard } from '@/components/ErrorCard'
import { Eyebrow } from '@/components/Eyebrow'
import { InsufficientEvidenceCard } from '@/components/InsufficientEvidenceCard'
import { LoadingCard } from '@/components/LoadingCard'
import { QuestionInput } from '@/components/QuestionInput'
import { StatusChip } from '@/components/StatusChip'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card } from '@/components/ui/card'
import type { ChatTurn } from '@/lib/chat'
import { countDocuments, formatCounts, type DocumentItem } from '@/lib/documents'

import {
  ERROR_MESSAGE,
  indexingDocuments,
  INSUFFICIENT_MESSAGE,
  readyDocuments,
  scannedFailure,
  transientFailure,
} from './fixtures'

const noop = () => {}

export function Screen({
  documents,
  turns,
  citations,
  isLoading = false,
}: {
  documents: DocumentItem[]
  turns: ChatTurn[]
  citations?: Record<string, number[]>
  isLoading?: boolean
}) {
  const counts = countDocuments(documents)
  return (
    <AppLayout
      sidebar={
        <DocumentSidebar
          documents={documents}
          citations={citations}
          onUpload={noop}
          onRetry={noop}
          onRemove={noop}
        />
      }
    >
      <ChatHeader counts={counts} />
      <ChatThread
        turns={turns}
        counts={counts}
        onUpload={noop}
        onRetry={noop}
        onRephrase={noop}
        className="flex-auto"
      />
      <QuestionInput readyCount={counts.ready} indexingCount={counts.indexing} isLoading={isLoading} />
    </AppLayout>
  )
}

export function ComponentStates() {
  return (
    <div className="flex min-h-screen flex-col gap-8 bg-background px-16 py-14">
      <div className="flex flex-col gap-1.5">
        <h1 className="m-0 text-display font-bold">Component states</h1>
        <p className="m-0 text-body text-muted-foreground">
          States used across the four screens. Red is reserved for failures; “Not enough evidence” is a
          normal outcome.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-3">
        <section className="flex flex-col gap-3">
          <Eyebrow>Document status (sidebar)</Eyebrow>
          {[indexingDocuments[2], readyDocuments[1]].map((document) => (
            <Card key={document.id} className="flex-row items-center justify-between rounded-lg px-3.5 py-3">
              <span className="text-body-sm font-medium">{document.filename}</span>
              <StatusChip status={document.status} />
            </Card>
          ))}
          <ul className="m-0 flex list-none flex-col gap-3 p-0">
            {[scannedFailure, transientFailure].map((document) => (
              <DocumentRow
                key={document.id}
                document={document}
                onUpload={noop}
                onRetry={noop}
                onRemove={noop}
              />
            ))}
          </ul>
        </section>

        <section className="flex flex-col gap-3">
          <Eyebrow>Answer states (chat)</Eyebrow>
          <LoadingCard />
          <InsufficientEvidenceCard message={INSUFFICIENT_MESSAGE} />
          <ErrorCard message={ERROR_MESSAGE} onRetry={noop} />
        </section>

        <section className="flex flex-col gap-3">
          <Eyebrow>Counts, input and upload</Eyebrow>
          <Card className="gap-1.5 rounded-xl px-4 py-3.5 text-label">
            <span className="font-semibold">Header and sidebar counts</span>
            {[[], indexingDocuments, readyDocuments].map((documents, index) => (
              <span key={index} className="text-foreground-tertiary">
                Documents: {formatCounts(countDocuments(documents))}
              </span>
            ))}
          </Card>
          <Card className="gap-2 rounded-xl p-0">
            <span className="px-4 pt-3.5 text-label font-semibold">Input when 0 documents are ready</span>
            <QuestionInput readyCount={0} indexingCount={3} className="border-0 px-4 pt-0 pb-3.5" />
          </Card>
          <Alert variant="destructive">
            <AlertTitle>Q3_Notes.docx wasn't added</AlertTitle>
            <AlertDescription>
              .docx is not supported. Upload a .pdf with selectable text, a .md or a .txt file.
            </AlertDescription>
          </Alert>
        </section>
      </div>
    </div>
  )
}
