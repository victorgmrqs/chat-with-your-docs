import { createCn } from 'cn/config'

/**
 * Merges class names and resolves Tailwind conflicts (the last one wins).
 *
 * Custom theme scales must be registered here. Without it, `text-caption` (a font size) would be
 * read as a text color and `cn('text-caption', 'text-muted-foreground')` would drop one of them.
 * Keep these lists in sync with `@theme` in src/styles/theme.css.
 */
export const cn = createCn({
  extend: {
    theme: {
      text: ['caption', 'label', 'body-sm', 'body', 'body-lg', 'title-sm', 'title', 'heading', 'display'],
      leading: ['snug', 'normal', 'relaxed'],
      tracking: ['eyebrow'],
    },
  },
})
