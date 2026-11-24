import { formatCounts, type DocumentCounts } from '@/lib/documents'

/** `counts` is left out while the document list is not known yet. */
export function ChatHeader({ counts }: { counts?: DocumentCounts }) {
  return (
    <header className="flex flex-col gap-1 border-b border-border px-10 py-5">
      <h1 className="m-0 text-title font-bold">Ask your documents</h1>
      {counts && <p className="m-0 text-label text-muted-foreground">Documents: {formatCounts(counts)}</p>}
    </header>
  )
}
