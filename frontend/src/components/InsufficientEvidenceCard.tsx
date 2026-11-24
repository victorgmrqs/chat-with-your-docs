import { ArrowUpFromLine, ZoomOut } from 'lucide-react'

import { Eyebrow } from '@/components/Eyebrow'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardFooter, CardTitle } from '@/components/ui/card'
import { locationLabel, type Passage } from '@/lib/chat'

interface InsufficientEvidenceCardProps {
  /** Fixed backend message (DOM-10), never model text. */
  message: string
  relatedPassage?: Passage | null
  onRephrase?: () => void
  onUpload?: () => void
}

/** "Not enough evidence" is an expected outcome: neutral colors, no citation number (DOM-15). */
export function InsufficientEvidenceCard({
  message,
  relatedPassage,
  onRephrase,
  onUpload,
}: InsufficientEvidenceCardProps) {
  const location = relatedPassage ? locationLabel(relatedPassage) : null

  return (
    <Card as="article" aria-label="Not enough evidence">
      <div className="flex items-start gap-3">
        <span className="inline-flex size-9 flex-none items-center justify-center rounded-lg bg-secondary text-foreground-tertiary">
          <ZoomOut aria-hidden="true" className="size-5" />
        </span>
        <div className="flex flex-col gap-1.5">
          <CardTitle as="h2">Not enough evidence</CardTitle>
          <p className="m-0 text-body leading-relaxed text-foreground-secondary">{message}</p>
        </div>
      </div>

      {relatedPassage && (
        <div className="flex flex-col gap-2.5">
          <Eyebrow as="h3">Related passage · does not answer this question</Eyebrow>
          <div className="flex flex-col gap-2.5 rounded-xl border-[1.5px] border-dashed border-related-passage-border bg-related-passage px-4 py-3.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="text-body-sm font-semibold text-foreground-tertiary">
                {relatedPassage.filename}
              </span>
              {location && (
                <Badge variant="outline" className="text-foreground-tertiary">
                  {location}
                </Badge>
              )}
            </div>
            <blockquote className="m-0 text-body-sm leading-relaxed text-foreground-tertiary">
              “{relatedPassage.passage}”
            </blockquote>
          </div>
        </div>
      )}

      {(onRephrase || onUpload) && (
        <CardFooter>
          {onRephrase && (
            <Button variant="outline" onClick={onRephrase}>
              Rephrase the question
            </Button>
          )}
          {onUpload && (
            <Button variant="outline" onClick={onUpload}>
              <ArrowUpFromLine aria-hidden="true" />
              Upload a relevant document
            </Button>
          )}
        </CardFooter>
      )}
    </Card>
  )
}
