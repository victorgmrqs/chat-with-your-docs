import { useMemo, useRef, useState, type ChangeEvent } from 'react'

import { AppLayout } from '@/components/AppLayout'
import { ChatHeader } from '@/components/ChatHeader'
import { ChatThread } from '@/components/ChatThread'
import { DocumentSidebar } from '@/components/DocumentSidebar'
import { ErrorCard } from '@/components/ErrorCard'
import { QuestionInput } from '@/components/QuestionInput'
import { useChat } from '@/hooks/useChat'
import { useDocuments } from '@/hooks/useDocuments'
import { useUpload } from '@/hooks/useUpload'
import { citedDocuments, type ChatTurn } from '@/lib/chat'
import { ACCEPTED_EXTENSIONS, countDocuments, type DocumentItem } from '@/lib/documents'

const ACCEPT = ACCEPTED_EXTENSIONS.map((extension) => `.${extension}`).join(',')

/** Citations of the latest finished answer; undefined before the first one (sidebar highlight). */
function latestCitations(turns: readonly ChatTurn[]): Record<string, number[]> | undefined {
  const latest = turns.findLast((turn) => turn.status === 'answered' || turn.status === 'insufficient')
  if (latest?.status === 'answered') return citedDocuments(latest.sources)
  return latest ? {} : undefined
}

/** `pollIntervalMs` overrides the DOM-19 polling interval (tests). */
function App({ pollIntervalMs }: { pollIntervalMs?: number }) {
  const { documents, listState, loadError, refresh, upsert } = useDocuments(pollIntervalMs)
  const { upload, rejection, fileFor } = useUpload(upsert)
  const { turns, isLoading, ask, retry } = useChat()
  const fileInput = useRef<HTMLInputElement>(null)
  // "Rephrase" puts the question back in the input by remounting it with that default value.
  const [draft, setDraft] = useState({ key: 0, question: '' })

  const counts = countDocuments(documents)
  const loaded = listState === 'loaded'
  const citations = useMemo(() => latestCitations(turns), [turns])

  const pickFiles = () => fileInput.current?.click()

  function onFilesPicked(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    event.target.value = '' // picking the same file again still fires change
    if (files.length > 0) void upload(files)
  }

  /** DOM-04: indexing_failed is retried by uploading the same file; after a reload, pick it. */
  function retryDocument(document: DocumentItem) {
    const file = fileFor(document.id)
    if (file) void upload([file])
    else pickFiles()
  }

  return (
    <AppLayout
      sidebar={
        <DocumentSidebar
          documents={documents}
          citations={citations}
          uploadRejection={rejection}
          onUpload={pickFiles}
          onRetry={retryDocument}
          listState={listState}
          // No onRemove: the API has no delete endpoint yet.
        />
      }
    >
      <input
        ref={fileInput}
        type="file"
        accept={ACCEPT}
        multiple
        hidden
        aria-label="Choose documents to upload"
        onChange={onFilesPicked}
      />
      <ChatHeader counts={loaded ? counts : undefined} />
      {loadError && (
        <div className="mx-10 mt-6">
          <ErrorCard title="Couldn't load your documents" message={loadError} onRetry={() => void refresh()} />
        </div>
      )}
      {loaded ? (
        <ChatThread
          turns={turns}
          counts={counts}
          onUpload={pickFiles}
          onRetry={retry}
          onRephrase={(turn) => setDraft((current) => ({ key: current.key + 1, question: turn.question }))}
          className="flex-auto"
        />
      ) : (
        <div className="flex-auto" />
      )}
      <QuestionInput
        key={draft.key}
        defaultValue={draft.question}
        readyCount={counts.ready}
        indexingCount={counts.indexing}
        isLoading={isLoading}
        onSubmit={ask}
      />
    </AppLayout>
  )
}

export default App
