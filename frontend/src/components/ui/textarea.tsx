import * as React from 'react'

import { cn } from '@/lib/utils'

function Textarea({ className, ...props }: React.ComponentProps<'textarea'>) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        'w-full min-w-0 resize-none rounded-lg border border-input bg-background px-3.5 py-3 text-body text-foreground transition-colors placeholder:text-muted-foreground focus-visible:border-ring disabled:cursor-not-allowed disabled:border-disabled disabled:bg-muted',
        className,
      )}
      {...props}
    />
  )
}

export { Textarea }
