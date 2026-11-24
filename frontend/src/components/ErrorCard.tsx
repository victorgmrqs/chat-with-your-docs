import { CircleAlert } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

interface ErrorCardProps {
  message: string
  title?: string
  onRetry?: () => void
}

/** A request that failed technically (DOM-12). Red is for failures only (DOM-15). */
export function ErrorCard({ message, title = "Couldn't get an answer", onRetry }: ErrorCardProps) {
  return (
    <Alert variant="destructive" className="gap-2.5 p-4">
      <AlertTitle className="flex items-center gap-2">
        <CircleAlert aria-hidden="true" className="size-4.5" />
        {title}
      </AlertTitle>
      <AlertDescription>{message}</AlertDescription>
      {onRetry && (
        <Button variant="outline" className="self-start justify-self-start" onClick={onRetry}>
          Retry
        </Button>
      )}
    </Alert>
  )
}
