import * as React from 'react'

import { cn } from '@/lib/utils'

// Borders carry the hierarchy; cards never get a shadow (DOM-14).
// `as="article"` for self-contained chat content (answers, loading, not enough evidence).
function Card({
  as: Tag = 'div',
  className,
  ...props
}: React.ComponentProps<'div'> & { as?: 'div' | 'article' }) {
  return (
    <Tag
      data-slot="card"
      className={cn(
        'flex flex-col gap-4 rounded-2xl border border-border bg-card p-5 text-card-foreground',
        className,
      )}
      {...props}
    />
  )
}

function CardHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-header"
      className={cn('flex flex-wrap items-center gap-x-3 gap-y-2', className)}
      {...props}
    />
  )
}

function CardTitle({
  as: Tag = 'div',
  className,
  ...props
}: React.ComponentProps<'div'> & { as?: 'div' | 'h2' | 'h3' }) {
  return <Tag data-slot="card-title" className={cn('m-0 text-title-sm font-bold', className)} {...props} />
}

function CardDescription({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-description"
      className={cn('text-label text-muted-foreground', className)}
      {...props}
    />
  )
}

function CardFooter({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-footer"
      className={cn('flex flex-wrap items-center gap-x-3 gap-y-2', className)}
      {...props}
    />
  )
}

export { Card, CardHeader, CardFooter, CardTitle, CardDescription }
