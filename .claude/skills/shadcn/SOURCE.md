# Source

- Upstream repo: https://github.com/shadcn-ui/ui
- Path: `skills/shadcn`
- Commit: 45bbf9ba23c9c0f63d38887947e5fb06f59c7da3
- License: MIT (see `LICENSE`, copied verbatim from the upstream repo root)
- Vendored: 2026-11-20
- Modified: yes

## Modifications

- Narrowed `description`; removed `allowed-tools`, `user-invocable` and the `!`-prefixed dynamic command that auto-ran `npx shadcn@latest info --json` on skill load.
- Added "Project overrides": Radix only, HEX tokens, light theme only, official `@shadcn` registry only, every CLI command proposed to the user first, pinned `shadcn@<pinned>` instead of `@latest`, no auto-fetching of docs URLs.
- SKILL.md: removed chat rules, community registries, presets/apply/init --force/monorepo, DESIGN.md design-system flow, `isRSC`, unpinned docs fetching, "Registry must be explicit" preset workflow; Toast is Sonner only.
- cli.md: reduced to add/search/view/info with pinned version; removed init, apply, docs, build, templates, presets.
- customization.md: OKLCH replaced by HEX; dark mode and `next-themes` removed; presets and Tailwind v3 removed.
- rules/styling.md: `cn` import fixed to `@/lib/utils`; `dark:` rule replaced by "no dark variants"; shimmer/scroll-fade section (chat-only) removed.
- rules/composition.md: chat primitives and Base UI toast removed. rules/forms.md: theme/dark examples replaced. rules/base-vs-radix.md: note that this project uses Radix.

## Dropped files

`mcp.md`, `registry.md`, `design-system.md`, `design-system-page.md`, `rules/chat.md`, `assets/`, `scripts/`, `evals/`, `agents/`.
