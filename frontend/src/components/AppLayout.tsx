import type { ReactNode } from 'react'

/**
 * Sidebar + main column. From `md` up it is an app shell of the viewport's height: the page does
 * not scroll, the sidebar stays in place (scrolling on its own if the list is long) and the main
 * column decides what scrolls (the conversation). Below `md` the columns stack (handoff flex-wrap
 * layout) and the page scrolls as usual.
 */
export function AppLayout({ sidebar, children }: { sidebar: ReactNode; children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-wrap bg-background text-foreground md:h-dvh md:flex-nowrap">
      <div className="scroll-area flex flex-[1_1_300px]">{sidebar}</div>
      <main className="flex min-w-0 flex-[999_1_560px] flex-col md:min-h-0">{children}</main>
    </div>
  )
}
