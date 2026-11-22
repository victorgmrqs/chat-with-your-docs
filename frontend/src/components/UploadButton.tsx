import { ArrowUpFromLine } from 'lucide-react'

import { Button } from '@/components/ui/button'

/** The "Upload documents" call to action (sidebar and empty collection). */
export function UploadButton({ onClick, size }: { onClick?: () => void; size?: 'default' | 'lg' }) {
  return (
    <Button size={size} onClick={onClick}>
      <ArrowUpFromLine aria-hidden="true" className="size-4.5" />
      Upload documents
    </Button>
  )
}
