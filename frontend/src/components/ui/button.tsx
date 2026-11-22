import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { Slot } from 'radix-ui'

import { cn } from '@/lib/utils'

// Adapted to the handoff: 44px touch targets, 10px radius, borders instead of shadows (DOM-14).
const buttonVariants = cva(
  "inline-flex shrink-0 cursor-pointer items-center justify-center gap-2 rounded-lg border border-transparent font-semibold whitespace-nowrap transition-colors outline-none select-none focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          'bg-primary text-primary-foreground hover:bg-primary-hover disabled:bg-disabled disabled:text-disabled-foreground',
        outline:
          'border-input bg-background text-foreground hover:bg-muted disabled:text-disabled-foreground',
        ghost: 'bg-transparent text-foreground-tertiary hover:bg-muted hover:text-foreground',
        link: 'bg-transparent text-primary hover:text-primary-hover hover:underline underline-offset-4',
      },
      size: {
        default: 'h-11 px-4 text-body-sm',
        sm: 'h-11 rounded-md px-3 text-label',
        lg: 'h-12 px-6 text-body',
        inline: 'h-11 gap-1.5 px-1 text-label',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

function Button({
  className,
  variant = 'default',
  size = 'default',
  asChild = false,
  ...props
}: React.ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : 'button'

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button }
