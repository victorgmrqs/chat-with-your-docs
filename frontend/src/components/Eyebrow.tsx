import * as React from 'react'

import { cn } from '@/lib/utils'

/** Small uppercase section label ("DOCUMENTS", "SOURCES (2)"); `as` keeps the outline right. */
export function Eyebrow({
  as: Tag = 'h2',
  className,
  ...props
}: React.ComponentProps<'h2'> & { as?: 'h2' | 'h3' }) {
  return (
    <Tag
      className={cn(
        'm-0 text-caption font-semibold tracking-eyebrow text-muted-foreground uppercase',
        className,
      )}
      {...props}
    />
  )
}
