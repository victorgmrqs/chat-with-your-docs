import { useId, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { locationLabel, type Source } from '@/lib/chat'
import { cn } from '@/lib/utils'

/** Passages longer than this start clamped to three lines with a "Show full passage" toggle. */
const LONG_PASSAGE = 200

/** One cited source: number, document, location (page or heading) and the stored passage. */
export function SourceCard({ source, id }: { source: Source; id?: string }) {
  const [expanded, setExpanded] = useState(false)
  const passageId = useId()
  const location = locationLabel(source)
  const long = source.passage.length > LONG_PASSAGE

  return (
    <li id={id} className="flex scroll-mt-6 flex-col gap-2.5 rounded-xl border border-border p-4">
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="inline-flex size-6 items-center justify-center rounded-sm bg-primary text-caption font-bold text-primary-foreground">
          {source.number}
        </span>
        <span className="text-body-sm font-semibold">{source.filename}</span>
        {location && <Badge variant="outline">{location}</Badge>}
      </div>
      <blockquote
        id={passageId}
        className={cn(
          'm-0 rounded-md bg-passage px-3.5 py-3 text-body-sm leading-relaxed text-passage-foreground',
          long && !expanded && 'line-clamp-3',
        )}
      >
        “{source.passage}”
      </blockquote>
      {long && (
        <Button
          variant="link"
          size="inline"
          className="self-start"
          aria-expanded={expanded}
          aria-controls={passageId}
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? 'Show less' : 'Show full passage'}
        </Button>
      )}
    </li>
  )
}
