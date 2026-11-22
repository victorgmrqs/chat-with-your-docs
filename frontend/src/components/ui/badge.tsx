import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { Slot } from 'radix-ui'

import { cn } from '@/lib/utils'

// Status variants use the status tokens only; red appears only for `failed` (DOM-15).
const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center gap-1 rounded-full px-2 py-0.75 text-caption font-semibold whitespace-nowrap [&>svg]:pointer-events-none [&>svg:not([class*='size-'])]:size-3",
  {
    variants: {
      variant: {
        indexing: 'bg-status-indexing text-status-indexing-foreground',
        ready: 'bg-status-ready text-status-ready-foreground',
        failed: 'bg-status-failed text-status-failed-foreground',
        outline: 'rounded-sm border border-input py-0.5 text-foreground-secondary',
      },
    },
    defaultVariants: {
      variant: 'outline',
    },
  },
)

function Badge({
  className,
  variant = 'outline',
  asChild = false,
  ...props
}: React.ComponentProps<'span'> & VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : 'span'

  return (
    <Comp
      data-slot="badge"
      data-variant={variant}
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge }
