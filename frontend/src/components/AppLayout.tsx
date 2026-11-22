import type { ReactNode } from 'react'

/** Sidebar + main column. Wraps to one column on narrow screens (handoff flex-wrap layout). */
export function AppLayout({ sidebar, children }: { sidebar: ReactNode; children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-wrap bg-background text-foreground">
      <div className="flex flex-[1_1_300px]">{sidebar}</div>
      <main className="flex min-w-0 flex-[999_1_560px] flex-col">{children}</main>
    </div>
  )
}
