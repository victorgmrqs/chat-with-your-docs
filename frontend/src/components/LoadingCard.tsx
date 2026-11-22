import { LoaderCircle } from 'lucide-react'

import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export function LoadingCard() {
  return (
    <Card as="article" aria-label="Answer in progress" aria-busy="true" className="gap-3.5">
      <div role="status" className="flex items-center gap-2.5 text-body-sm font-semibold text-primary">
        <LoaderCircle aria-hidden="true" strokeWidth={2.25} className="size-4.5 motion-safe:animate-spin" />
        Searching your documents…
      </div>
      <div className="flex flex-col gap-2.5">
        <Skeleton className="w-full" />
        <Skeleton className="w-11/12" />
        <Skeleton className="w-2/3" />
      </div>
    </Card>
  )
}
