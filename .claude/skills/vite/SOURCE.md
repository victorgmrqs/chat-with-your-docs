# Source

- Upstream: https://github.com/antfu/skills
- Path: `skills/vite`
- Commit: 4a6bb39e7b45e26402eb215393c51ccf5df1ca4c
- License: MIT (see `LICENSE`)
- Vendored: 2026-11-20
- Modified: yes

## Modifications

- Frontmatter: narrowed `description` (SPA config, env vars, assets, dev proxy), added `license`, removed upstream-specific fields.
- Added "Project overrides" section (SPA only, `VITE_` prefix, proxy to FastAPI, ask before installing, Vite 8 targeting note).
- Removed Vue plugins, `--ssr` CLI example and SSR/library-mode mentions; Vue plugin example in core-config replaced with the React plugin.
- Fixed index tables so they only reference vendored files.

## Dropped files

`GENERATION.md`, `references/build-and-ssr.md`, `references/environment-api.md`, `references/rolldown-migration.md`, `references/core-plugin-api.md`.
