# Source

- Upstream repo: https://github.com/vercel-labs/agent-skills
- Path: `skills/web-design-guidelines`
- Commit: 5a37a6329fbad3666c3207392a6a7c0110e92efb
- License: MIT. The upstream repo has no LICENSE file; the license is declared in the upstream README and SKILL.md frontmatter. `LICENSE` here is a standard MIT notice, "Copyright (c) Vercel, Inc."
- `references/command.md` originates from https://github.com/vercel-labs/web-interface-guidelines at commit 434b7f91364665f2f733b310ec54809bf8f37937 (license per the upstream README).
- Vendored: 2026-11-20
- Modified: yes

## Modifications

- SKILL.md: narrowed description, added "Project overrides", removed the "Updating the Guidelines" maintainer section (`gh api` / `curl`), replaced the pinned SHA-256 (file is now edited).
- references/command.md: removed Hydration Safety rules (kept the controlled-input rule); removed Dark Mode rules (kept `theme-color`); removed the `priority` image prop; replaced `nuqs` with router search params / `URLSearchParams`; softened the keyboard-handler rule so native buttons need no extra handlers; Title Case rule now follows the project convention.

## Dropped files

None. Both upstream files are kept.
