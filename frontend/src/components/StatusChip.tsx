import { Check, CircleAlert, LoaderCircle, type LucideIcon } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import type { DocumentStatus } from '@/lib/documents'
import { cn } from '@/lib/utils'

const STATUS: Record<DocumentStatus, { label: string; Icon: LucideIcon; iconClassName?: string }> = {
  indexing: { label: 'Indexing…', Icon: LoaderCircle, iconClassName: 'motion-safe:animate-spin' },
  ready: { label: 'Ready', Icon: Check },
  failed: { label: 'Failed', Icon: CircleAlert },
}

/** Document status; red only for Failed (DOM-15). */
export function StatusChip({ status, className }: { status: DocumentStatus; className?: string }) {
  const { label, Icon, iconClassName } = STATUS[status]

  return (
    <Badge variant={status} className={cn('flex-none', className)}>
      <Icon aria-hidden="true" strokeWidth={3} className={iconClassName} />
      {label}
    </Badge>
  )
}
