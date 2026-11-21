# Source

- Upstream: https://github.com/antfu/skills
- Path: `skills/vitest`
- Commit: 4a6bb39e7b45e26402eb215393c51ccf5df1ca4c
- License: MIT (see `LICENSE`)
- Vendored: 2026-11-20
- Modified: yes

## Modifications

- Frontmatter: narrowed `description` (unit/integration tests run by Vitest only), added `license`.
- Added "Project overrides" section, including the list of v5-only behaviours to verify (upstream was written against Vitest 5.1.0-beta.1).
- Removed all Browser Mode content (advanced-environments, snapshots, config, CLI); environments reduced to jsdom (happy-dom and edge-runtime removed).
- features-mocking: `vi.stubGlobal('fetch')` replaced by a warning; added MSW section and a Testing Library pointer.
- Removed benchmarking, tags and concurrency cross-references and the benchmark section; fixture example no longer uses Playwright `page`.
- Install commands marked "ask the user first".

## Dropped files

`GENERATION.md`, `references/features-benchmarking.md`, `references/features-concurrency.md`, `references/features-test-tags.md`, `references/features-reporters.md`, `references/advanced-projects.md`.
