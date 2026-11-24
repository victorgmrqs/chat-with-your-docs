import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

// `info` is the neutral banner (e.g. "only Ready documents are searched"); `destructive` is
// reserved for failures (DOM-15).
const alertVariants = cva(
  "group grid w-full gap-1 text-left has-[>svg]:grid-cols-[auto_1fr] has-[>svg]:gap-x-3 *:[svg]:row-span-2 *:[svg]:mt-0.5 *:[svg]:text-current *:[svg:not([class*='size-'])]:size-5",
  {
    variants: {
      variant: {
        info: 'rounded-lg bg-info-subtle px-4 py-3 text-body-sm text-info',
        destructive:
          'rounded-xl border border-destructive-border bg-destructive-subtle px-4 py-3.5 text-destructive',
      },
    },
    defaultVariants: {
      variant: 'info',
    },
  },
)

function Alert({
  className,
  variant = 'info',
  ...props
}: React.ComponentProps<'div'> & VariantProps<typeof alertVariants>) {
  return (
    <div
      data-slot="alert"
      role={variant === 'destructive' ? 'alert' : 'status'}
      className={cn(alertVariants({ variant }), className)}
      {...props}
    />
  )
}

function AlertTitle({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="alert-title"
      className={cn('text-body-sm font-bold group-has-[>svg]:col-start-2', className)}
      {...props}
    />
  )
}

function AlertDescription({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="alert-description"
      className={cn('text-label text-foreground-secondary', className)}
      {...props}
    />
  )
}

export { Alert, AlertTitle, AlertDescription }
