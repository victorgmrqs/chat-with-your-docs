# Source

- Upstream: https://github.com/microsoft/playwright-cli
- Path: `skills/playwright-cli`
- Commit: c872a33cec77fa03c28fa7c6d1ad99d15d04ce42
- License: Apache-2.0 (see `LICENSE`)
- Vendored: 2026-11-20
- Modified: yes. Per Apache-2.0 section 4(b), these files carry prominent notice that they were changed from the originals.

## Modifications

- Frontmatter: removed `allowed-tools` (it pre-approved Bash for `playwright-cli`/`npx playwright`, including `run-code`, install and attach); narrowed `description` to E2E testing and debugging of this project's frontend; added `license`.
- Added "Project overrides" section: base URL from the Compose stack, headless default, credentials from fixtures/env, sensitive artifacts under `.playwright-cli/` (gitignored) and deleted after use, locally pinned `npx --no-install`, never install without asking.
- Removed `attach --extension` / `attach --cdp` (user's real browser) and `detach` sections, the Windows `&` section, the WebMCP section, video commands, the interactive `show --annotate` example, the PR attachments section, and the `npm install -g @playwright/cli@latest` installation instructions (replaced by an ask-first rule).
- Replaced literal passwords/emails and example URLs with `$E2E_USER`, `$E2E_PASSWORD`, `$E2E_BASE_URL` or `process.env` values; `state-save` paths moved under `.playwright-cli/`.
- Removed the `networkidle` example and the concurrent scraping and multi-page scraping examples; replaced `npm init playwright@latest` with an ask-first rule.
- Added a security section to tracing.md and security notes to storage-state.md.
- Fixed the index so it only references vendored files.

## Dropped files

`references/pr-attachments.md`, `references/video-recording.md`.
