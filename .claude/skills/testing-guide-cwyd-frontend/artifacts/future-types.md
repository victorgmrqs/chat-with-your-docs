> Part of the `testing-guide-cwyd-frontend` skill (see `../SKILL.md`).

# Future types (not in the codebase yet)

## Streaming chat view
- **What:** tokens appear progressively in an `aria-live` region; citations render when the
  final event arrives; an error event shows a failure state and keeps the question for retry.
- **Layer:** component test with an MSW handler from `msw/sse` emitting a scripted sequence of
  events; `await findBy*` for the final state.
- **Skip:** timing of individual tokens.

## Upload form
- **What:** accepted types (.pdf, .md, .txt) and size limit rejected before the request;
  accepted file shows progress then the document in the list; server rejection shows the API
  message.
- **Layer:** component test with `user.upload(input, file)` and MSW; one Playwright journey for
  the real upload.

## shadcn/ui compositions (dialogs, forms built from `src/components/ui/`)
- **What:** your behavior on top of the primitive — confirm dialog deletes only after confirm,
  focus returns to the trigger, form shows field errors.
- **Layer:** component test. Radix renders dialogs in a portal; query with `screen`, which
  covers the whole document.
- **Skip:** primitive behavior (open/close animations, keyboard handling Radix already provides).

## Formatting utilities (`src/lib/**`)
- **What:** only utilities with branching (relative dates, file sizes, score labels).
- **Layer:** unit test (plain Vitest, no DOM); small inline snapshots are acceptable for
  formatted values.

## Routing (if a router is added)
- **What:** unknown route shows the not-found state; deep link to a document opens it.
- **Layer:** component test rendering the router with an initial entry; nginx fallback is
  proven by Playwright.
