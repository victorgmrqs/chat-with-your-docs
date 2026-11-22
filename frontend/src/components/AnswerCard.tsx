import { Check, ChevronRight } from 'lucide-react'
import { useId, type ReactNode } from 'react'

import { Eyebrow } from '@/components/Eyebrow'
import { SourceCard } from '@/components/SourceCard'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { locationLabel, type Source } from '@/lib/chat'

interface AnswerCardProps {
  answer: string
  sources: readonly Source[]
  /** Earlier answers are shown compact, with their sources collapsed. */
  compact?: boolean
}

const CITATION_CHIP =
  'mx-0.5 inline-flex h-5.5 min-w-5.5 items-center justify-center rounded-sm bg-citation px-1.5 align-[2px] text-caption font-bold text-citation-foreground no-underline'

/**
 * Replaces the `[n]` markers of the answer with citation chips. Only numbers present in `sources`
 * become chips: the citations come from the API's sources, never from parsing chunk ids (DOM-09).
 */
function renderAnswer(answer: string, sources: readonly Source[], anchor?: (n: number) => string) {
  const byNumber = new Map(sources.map((source) => [source.number, source]))
  // split() with a capture group puts the [n] markers at the odd indices.
  return answer.split(/(\[\d+\])/).map((part, index): ReactNode => {
    const source = index % 2 === 1 ? byNumber.get(Number(part.slice(1, -1))) : undefined
    if (!source) return part
    const location = locationLabel(source)
    const label = `Source ${source.number}: ${source.filename}${location ? `, ${location.toLowerCase()}` : ''}`
    const Chip = anchor ? 'a' : 'span'
    return (
      <Chip
        key={index}
        href={anchor ? `#${anchor(source.number)}` : undefined}
        aria-label={label}
        className={CITATION_CHIP}
      >
        {source.number}
      </Chip>
    )
  })
}

export function AnswerCard({ answer, sources, compact = false }: AnswerCardProps) {
  const prefix = useId()
  const anchor = (n: number) => `${prefix}-source-${n}`
  const sourceList = (
    <ol className="m-0 flex list-none flex-col gap-3 p-0">
      {sources.map((source) => (
        <SourceCard key={source.chunkId} source={source} id={compact ? undefined : anchor(source.number)} />
      ))}
    </ol>
  )
  const plural = sources.length === 1 ? 'source' : 'sources'

  if (compact) {
    return (
      <Card as="article" aria-label="Earlier answer" className="gap-3 py-4">
        <p className="m-0 text-body leading-relaxed text-foreground-secondary">
          {renderAnswer(answer, sources)}
        </p>
        <Collapsible className="flex flex-col gap-3">
          <CollapsibleTrigger asChild>
            <Button variant="link" size="inline" className="group self-start">
              <ChevronRight
                aria-hidden="true"
                className="transition-transform group-data-[state=open]:rotate-90"
              />
              <span className="truncate">
                Show {sources.length} {plural} · {[...new Set(sources.map((s) => s.filename))].join(', ')}
              </span>
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>{sourceList}</CollapsibleContent>
        </Collapsible>
      </Card>
    )
  }

  return (
    <Card as="article" aria-label="Answer">
      <CardHeader className="gap-x-3">
        <h2 className="m-0 inline-flex items-center gap-1.5 text-label font-bold text-success">
          <Check aria-hidden="true" strokeWidth={2.5} className="size-4" />
          Answer
        </h2>
        <CardDescription>
          {sources.length} {plural}
        </CardDescription>
      </CardHeader>
      <p className="m-0 text-body-lg leading-relaxed">{renderAnswer(answer, sources, anchor)}</p>
      <div className="flex flex-col gap-3 border-t border-border pt-4">
        <Eyebrow as="h3">Sources ({sources.length})</Eyebrow>
        {sourceList}
      </div>
    </Card>
  )
}
