---
name: shadcn
description: Add, compose and style shadcn/ui components (Radix) in this project's React + Vite SPA. Use when adding a shadcn component, composing forms/dialogs/cards from existing ones, or fixing shadcn usage (variants, icons, spacing, semantic tokens). Not for backend, tests, or non-UI work.
license: MIT
---

## Project overrides

These project rules win over anything below:

- Stack: React + Vite + TypeScript SPA, Tailwind v4 (`@theme inline`), shadcn/ui on **Radix** (`base: radix`). Follow `(radix)` examples; use `asChild`, never `render`.
- No Next.js, RSC or `"use client"`. Everything is client-side.
- Colors are **HEX design tokens only** (no OKLCH). Use semantic classes (`bg-primary`, `bg-muted`, `text-muted-foreground`), never hardcoded colors or Tailwind palette classes (`bg-gray-200`, `text-emerald-600`). Red is reserved for failures (destructive).
- **Light theme only.** No dark mode, no `dark:` variants, no `next-themes`.
- Font is Inter. Icons come from the library in `components.json` (`iconLibrary`).
- Only the **official `@shadcn` registry**. No community registries (`@magicui`, `@bundui`, ...), no URL or `owner/repo` items, no `--all`.
- **Never run a CLI command without asking the user first.** Propose the exact command and wait for confirmation. Never install packages or run `npx shadcn` on your own.
- Use the pinned CLI version from `frontend/package.json` (shown as `shadcn@<pinned>` below), never `@latest`.
- Do not auto-fetch documentation URLs. Read the installed component source in `components/ui` and the rules in this skill; fetch a URL only if the user asks.
- Presets, `apply`, `init --force`, monorepo scaffolding and DESIGN.md design-system generation are out of scope.
- Toasts use `sonner`.

# shadcn/ui

Components are added as source code to the project (`components/ui`). Compose and restyle them with semantic tokens; do not reinvent them.

## Project context

Read `components.json` and the Tailwind CSS file it points to for project context (`aliases`, `iconLibrary`, `tailwind.css`, `base`). If you need the CLI's resolved view, propose `npx shadcn@<pinned> info --json` to the user and wait for approval. See [cli.md](./cli.md).

## Principles

1. **Use existing components first.** Check `components/ui` and the official `@shadcn` registry before writing custom UI.
2. **Compose, don't reinvent.** Settings page = Tabs + Card + form controls. Dashboard = Sidebar + Card + Chart + Table.
3. **Use built-in variants before custom styles.** `variant="outline"`, `size="sm"`, etc.
4. **Use semantic colors.** `bg-primary`, `text-muted-foreground`, never raw values like `bg-blue-500`.

## Critical Rules

These rules are **always enforced**. Each links to a file with Incorrect/Correct code pairs.

### Styling & Tailwind → [styling.md](./rules/styling.md)

- **`className` for layout, not styling.** Never override component colors or typography.
- **No `space-x-*` or `space-y-*`.** Use `flex` with `gap-*`. For vertical stacks, `flex flex-col gap-*`.
- **Use `size-*` when width and height are equal.** `size-10` not `w-10 h-10`.
- **Use `truncate` shorthand.** Not `overflow-hidden text-ellipsis whitespace-nowrap`.
- **No `dark:` variants.** Light theme only; use semantic tokens (`bg-background`, `text-muted-foreground`).
- **Use `cn()` for conditional classes** (import from `@/lib/utils`). Don't write manual template literal ternaries.
- **No manual `z-index` on overlay components.** Dialog, Sheet, Popover, etc. handle their own stacking.

### Forms & Inputs → [forms.md](./rules/forms.md)

- **Forms use `FieldGroup` + `Field`.** Never use raw `div` with `space-y-*` or `grid gap-*` for form layout.
- **`InputGroup` uses `InputGroupInput`/`InputGroupTextarea`.** Never raw `Input`/`Textarea` inside `InputGroup`.
- **Buttons inside inputs use `InputGroup` + `InputGroupAddon`.**
- **Option sets (2-7 choices) use `ToggleGroup`.** Don't loop `Button` with manual active state.
- **`FieldSet` + `FieldLegend` for grouping related checkboxes/radios.** Don't use a `div` with a heading.
- **Field validation uses `data-invalid` + `aria-invalid`.** `data-invalid` on `Field`, `aria-invalid` on the control. For disabled: `data-disabled` on `Field`, `disabled` on the control.

### Component Structure → [composition.md](./rules/composition.md)

- **Items always inside their Group.** `SelectItem` → `SelectGroup`. `DropdownMenuItem` → `DropdownMenuGroup`. `CommandItem` → `CommandGroup`.
- **Use `asChild` for custom triggers** (Radix). → [base-vs-radix.md](./rules/base-vs-radix.md)
- **Dialog, Sheet, and Drawer always need a Title.** `DialogTitle`, `SheetTitle`, `DrawerTitle` required for accessibility. Use `className="sr-only"` if visually hidden.
- **Use full Card composition.** `CardHeader`/`CardTitle`/`CardDescription`/`CardContent`/`CardFooter`. Don't dump everything in `CardContent`.
- **Button has no `isPending`/`isLoading`.** Compose with `Spinner` + `data-icon` + `disabled`.
- **`TabsTrigger` must be inside `TabsList`.** Never render triggers directly in `Tabs`.
- **`Avatar` always needs `AvatarFallback`.** For when the image fails to load.

### Use Components, Not Custom Markup → [composition.md](./rules/composition.md)

- **Use existing components before custom markup.** Check if a component exists before writing a styled `div`.
- **Callouts use `Alert`.** Don't build custom styled divs.
- **Empty states use `Empty`.** Don't build custom empty state markup.
- **Toasts use `toast()` from `sonner`.**
- **Use `Separator`** instead of `<hr>` or `<div className="border-t">`.
- **Use `Skeleton`** for loading placeholders. No custom `animate-pulse` divs.
- **Use `Badge`** instead of custom styled spans.

### Icons → [icons.md](./rules/icons.md)

- **Icons in `Button` use `data-icon`.** `data-icon="inline-start"` or `data-icon="inline-end"` on the icon.
- **No sizing classes on icons inside components.** Components handle icon sizing via CSS. No `size-4` or `w-4 h-4`.
- **Pass icons as objects, not string keys.** `icon={CheckIcon}`, not a string lookup.

## Key Patterns

These are the most common patterns that differentiate correct shadcn/ui code. For edge cases, see the linked rule files above.

```tsx
// Form layout: FieldGroup + Field, not div + Label.
<FieldGroup>
  <Field>
    <FieldLabel htmlFor="email">Email</FieldLabel>
    <Input id="email" />
  </Field>
</FieldGroup>

// Validation: data-invalid on Field, aria-invalid on the control.
<Field data-invalid>
  <FieldLabel>Email</FieldLabel>
  <Input aria-invalid />
  <FieldDescription>Invalid email.</FieldDescription>
</Field>

// Icons in buttons: data-icon, no sizing classes.
<Button>
  <SearchIcon data-icon="inline-start" />
  Search
</Button>

// Spacing: gap-*, not space-y-*.
<div className="flex flex-col gap-4">  // correct
<div className="space-y-4">           // wrong

// Equal dimensions: size-*, not w-* h-*.
<Avatar className="size-10">   // correct
<Avatar className="w-10 h-10"> // wrong

// Status colors: Badge variants or semantic tokens, not raw colors.
<Badge variant="secondary">+20.1%</Badge>    // correct
<span className="text-emerald-600">+20.1%</span> // wrong
```

## Component Selection

| Need                       | Use                                                                                                 |
| -------------------------- | --------------------------------------------------------------------------------------------------- |
| Button/action              | `Button` with appropriate variant                                                                   |
| Form inputs                | `Input`, `Select`, `Combobox`, `Switch`, `Checkbox`, `RadioGroup`, `Textarea`, `InputOTP`, `Slider` |
| Toggle between 2-5 options | `ToggleGroup` + `ToggleGroupItem`                                                                   |
| Data display               | `Table`, `Card`, `Badge`, `Avatar`                                                                  |
| Navigation                 | `Sidebar`, `NavigationMenu`, `Breadcrumb`, `Tabs`, `Pagination`                                     |
| Overlays                   | `Dialog` (modal), `Sheet` (side panel), `Drawer` (bottom sheet), `AlertDialog` (confirmation)       |
| Feedback                   | `sonner`, `Alert`, `Progress`, `Skeleton`, `Spinner`                                                |
| Command palette            | `Command` inside `Dialog`                                                                           |
| Charts                     | `Chart` (wraps Recharts)                                                                            |
| Layout                     | `Card`, `Separator`, `Resizable`, `ScrollArea`, `Accordion`, `Collapsible`                          |
| Empty states               | `Empty`                                                                                             |
| Menus                      | `DropdownMenu`, `ContextMenu`, `Menubar`                                                            |
| Tooltips/info              | `Tooltip`, `HoverCard`, `Popover`                                                                   |

## Key Fields (`components.json`)

- **`aliases`** → use the actual alias prefix for imports (`@/`), never hardcode another.
- **`tailwind.css`** → the global CSS file where custom CSS variables are defined. Always edit this file, never create a new one.
- **`style`** → component visual treatment.
- **`base`** → must be `radix`. Affects component APIs and available props.
- **`iconLibrary`** → determines icon imports. Never assume `lucide-react`.
- **`aliases.utils`** → location of `cn()` (`@/lib/utils`).

## Workflow

1. **Get project context.** Read `components.json` and list `components/ui`.
2. **Check installed components first.** Before proposing an `add`, check that the component is not already present. Don't import components that haven't been added, and don't re-add ones already installed.
3. **Read before writing.** Read the installed component's source for its exact API. If it is not installed, tell the user which official `@shadcn` item you need.
4. **Propose the add.** Show the user the exact command, for example `npx shadcn@<pinned> add button card dialog`, and wait for confirmation. Preview with `--dry-run` first when updating existing components (see [Updating Components](#updating-components)).
5. **Review added components.** After a component is added, **read the added files and verify they are correct**. Check for missing sub-components (e.g. `SelectItem` without `SelectGroup`), missing imports, incorrect composition, hardcoded colors, `dark:` variants, or violations of the [Critical Rules](#critical-rules). Replace icon imports with the project's `iconLibrary`. Fix all issues before moving on.
6. **Official registry only.** Items come from `@shadcn`. If the user asks for a component from another registry, stop and ask.

## Updating Components

When the user asks to update a component from upstream while keeping local changes, use `--dry-run` and `--diff` (each proposed to the user first). **Never fetch raw files from GitHub manually.**

1. Propose `npx shadcn@<pinned> add <component> --dry-run` to see all files that would be affected.
2. For each file, propose `npx shadcn@<pinned> add <component> --diff <file>` to see what changed upstream vs local.
3. Decide per file based on the diff:
   - No local changes → safe to overwrite.
   - Has local changes → read the local file, analyze the diff, and apply upstream updates while preserving local modifications.
4. **Never use `--overwrite` without the user's explicit approval.**

## Quick Reference

Every command below is proposed to the user for confirmation before it runs. `shadcn@<pinned>` is the version recorded in `frontend/package.json`.

```bash
# Add official components.
npx shadcn@<pinned> add button card dialog

# Preview changes before adding/updating.
npx shadcn@<pinned> add button --dry-run
npx shadcn@<pinned> add button --diff button.tsx

# Search the official registry.
npx shadcn@<pinned> search @shadcn -q "sidebar"

# View registry item details (for items not yet installed).
npx shadcn@<pinned> view @shadcn/button
```

## Detailed References

- [rules/forms.md](./rules/forms.md) - FieldGroup, Field, InputGroup, ToggleGroup, FieldSet, validation states
- [rules/composition.md](./rules/composition.md) - Groups, overlays, Card, Tabs, Avatar, Alert, Empty, Toast, Separator, Skeleton, Badge, Button loading
- [rules/icons.md](./rules/icons.md) - data-icon, icon sizing, passing icons as objects
- [rules/styling.md](./rules/styling.md) - Semantic colors, variants, className, spacing, size, truncate, cn(), z-index
- [rules/base-vs-radix.md](./rules/base-vs-radix.md) - asChild vs render, Select, ToggleGroup, Slider, Accordion (this project uses Radix)
- [cli.md](./cli.md) - Commands and flags
- [customization.md](./customization.md) - Theming with HEX tokens, extending components
