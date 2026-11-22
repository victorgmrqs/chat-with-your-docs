import { File } from 'lucide-react'

import { BrandMark } from '@/components/BrandMark'
import { Eyebrow } from '@/components/Eyebrow'
import { StatusChip } from '@/components/StatusChip'
import { UploadButton } from '@/components/UploadButton'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  ACCEPTED_FORMATS,
  countDocuments,
  formatCounts,
  type DocumentItem,
} from '@/lib/documents'
import { cn } from '@/lib/utils'

export interface UploadRejection {
  filename: string
  /** Backend message (DOM-01), e.g. ".docx is not supported. Upload a .pdf …". */
  message: string
}

interface DocumentSidebarProps {
  documents: readonly DocumentItem[]
  /**
   * Document id → citation numbers of the latest answer. Undefined before any answer;
   * an empty object when the latest answer cites nothing.
   */
  citations?: Readonly<Record<string, number[]>>
  uploadRejection?: UploadRejection | null
  onUpload?: () => void
  onRetry?: (document: DocumentItem) => void
  onRemove?: (document: DocumentItem) => void
  className?: string
}

export function DocumentSidebar({
  documents,
  citations,
  uploadRejection,
  onUpload,
  onRetry,
  onRemove,
  className,
}: DocumentSidebarProps) {
  const counts = countDocuments(documents)
  const hasCitations = citations !== undefined && Object.keys(citations).length > 0

  return (
    <aside
      aria-label="Documents"
      className={cn('flex flex-1 flex-col gap-5 border-r border-border bg-sidebar px-5 py-6', className)}
    >
      <div className="flex items-center gap-2.5">
        <BrandMark />
        <span className="text-body-lg font-bold">Chat With Your Docs</span>
      </div>

      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <Eyebrow>Documents</Eyebrow>
        <span aria-live="polite" className="text-label text-muted-foreground">
          {formatCounts(counts)}
        </span>
      </div>

      <div className="flex flex-col gap-1.5">
        <UploadButton onClick={onUpload} />
        <span className="text-center text-caption text-muted-foreground">{ACCEPTED_FORMATS}</span>
      </div>

      {uploadRejection && (
        <Alert variant="destructive">
          <AlertTitle>{uploadRejection.filename} wasn't added</AlertTitle>
          <AlertDescription>{uploadRejection.message}</AlertDescription>
        </Alert>
      )}

      {documents.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border-[1.5px] border-dashed border-input px-4 py-6 text-center">
          <File aria-hidden="true" strokeWidth={1.75} className="size-6 text-muted-foreground" />
          <p className="m-0 text-body-sm font-semibold">No documents yet</p>
          <p className="m-0 text-label text-muted-foreground">
            Files you upload appear here with their status.
          </p>
        </div>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {documents.map((document) => (
            <DocumentRow
              key={document.id}
              document={document}
              citedAs={citations?.[document.id]}
              onUpload={onUpload}
              onRetry={onRetry}
              onRemove={onRemove}
            />
          ))}
        </ul>
      )}

      <div className="mt-auto flex flex-col gap-2 text-caption text-muted-foreground">
        {hasCitations && (
          <span className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="size-3 flex-none rounded-xs border-[1.5px] border-highlight-border bg-highlight"
            />
            Highlighted = cited in the latest answer
          </span>
        )}
        {citations !== undefined && !hasCitations && (
          <span>No document is highlighted: the latest answer cites no sources.</span>
        )}
        <span>Only Ready documents can be searched.</span>
      </div>
    </aside>
  )
}

interface DocumentRowProps {
  document: DocumentItem
  citedAs?: number[]
  onUpload?: () => void
  onRetry?: (document: DocumentItem) => void
  onRemove?: (document: DocumentItem) => void
}

export function DocumentRow({ document, citedAs, onUpload, onRetry, onRemove }: DocumentRowProps) {
  const failed = document.status === 'failed'
  const cited = citedAs !== undefined && citedAs.length > 0
  // Transient failures retry by uploading the same file again; permanent ones need another file.
  const fixAction = document.canRetry
    ? onRetry && { label: 'Retry', run: () => onRetry(document) }
    : onUpload && { label: 'Upload another file', run: onUpload }

  return (
    <li
      className={cn(
        'flex min-h-11 gap-2.5 rounded-lg border bg-background px-3 py-2.5',
        failed || cited ? 'items-start' : 'items-center',
        failed && 'border-destructive-border',
        cited && 'border-[1.5px] border-highlight-border bg-highlight',
      )}
    >
      <File
        aria-hidden="true"
        strokeWidth={1.75}
        className={cn('size-5 flex-none', cited ? 'text-primary' : 'text-muted-foreground')}
      />
      <div className="flex min-w-0 flex-auto flex-col gap-1">
        <span
          className={cn('truncate text-body-sm', cited ? 'font-semibold' : 'font-medium')}
          title={document.filename}
        >
          {document.filename}
        </span>
        {cited && (
          <span className="text-caption font-semibold text-highlight-foreground">
            Cited as source {citedAs.join(', ')}
          </span>
        )}
        {failed && (
          <>
            {document.failureMessage && (
              <span className="text-caption leading-snug text-destructive">
                {document.failureMessage}
              </span>
            )}
            {(fixAction || onRemove) && (
              <div className="mt-0.5 flex flex-wrap gap-2">
                {fixAction && (
                  <Button variant="outline" size="sm" onClick={fixAction.run}>
                    {fixAction.label}
                  </Button>
                )}
                {onRemove && (
                  <Button variant="ghost" size="sm" onClick={() => onRemove(document)}>
                    Remove
                  </Button>
                )}
              </div>
            )}
          </>
        )}
      </div>
      <StatusChip status={document.status} />
    </li>
  )
}
