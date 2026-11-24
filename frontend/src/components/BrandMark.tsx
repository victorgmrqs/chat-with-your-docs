import { cn } from '@/lib/utils'

/** The brand symbol (_docs/design/brand): a page that is also a chat bubble. */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true" className={cn('size-8 shrink-0', className)}>
      <rect width="64" height="64" rx="14" className="fill-primary" />
      <path
        d="M21 13H37L47 23V41Q47 45 43 45H28L17 53V17Q17 13 21 13Z"
        className="fill-primary-foreground"
      />
      <path d="M37 13V20Q37 23 40 23H47Z" className="fill-brand-detail" />
      <rect x="23" y="19" width="9" height="5" rx="2.5" className="fill-brand-detail" />
      <rect x="23" y="29" width="18" height="6" rx="3" className="fill-primary" />
    </svg>
  )
}
