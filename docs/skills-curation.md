# Skills curation

Third-party agent skills are treated as untrusted code. Before a skill entered
`.claude/skills/`, every file in it was read in full at a pinned commit and checked for:

1. **Prompt injection / hidden instructions**: text addressed to the agent that overrides
   instructions, widens scope or asks it to act silently (including HTML comments, link titles,
   alt text and frontmatter).
2. **Invisible or obfuscated content**: zero-width and bidi characters, non-ASCII outside normal
   typography, base64 or other encoded blobs.
3. **Network and exfiltration**: URLs fetched at runtime, telemetry, reading env vars, secrets,
   cookies or files outside the project.
4. **Execution**: scripts, hooks, auto-executed commands, package installs, `allowed-tools`
   pre-approvals, git/settings changes.
5. **Fit**: conflicts with this project's rules (`CLAUDE.md`, `.claude/rules/`).

Each vendored skill is an edited copy. It keeps the upstream `LICENSE`, adds a `SOURCE.md`
(repo, path, commit, list of modifications and dropped files) and starts with a
**Project overrides** section that wins over the upstream text. Vendored on 2026-11-20.

## Summary

| Skill (local name) | Upstream | Commit | License | Security | Decision |
|---|---|---|---|---|---|
| `fastapi` | fastapi/fastapi `.agents/skills/fastapi` | `05e6df7e` | MIT | Pass | Adopted with edits |
| `postgres-best-practices` | supabase/agent-skills `supabase-postgres-best-practices` | `c9be0e93` | MIT | Pass (notes) | Adopted with heavy edits |
| `pgvector-semantic-search` | timescale/pg-aiguide | `1aef6e45` | Apache-2.0 | Pass | Adopted with edits |
| `python-tooling` | original (inspired by trailofbits/skills `modern-python`) | — | — | n/a | Written for this project |
| `react-spa-performance` | vercel-labs/agent-skills `react-best-practices` | `5a37a632` | MIT | Pass | Adopted with edits (16 of 70 rules dropped) |
| `shadcn` | shadcn-ui/ui `skills/shadcn` | `45bbf9ba` | MIT | **Fail as shipped**, fixed | Adopted with heavy edits |
| `web-design-guidelines` | vercel-labs/agent-skills | `5a37a632` | MIT | Pass | Adopted with light edits |
| `vite` | antfu/skills | `4a6bb39e` | MIT | Pass | Adopted with edits |
| `vitest` | antfu/skills | `4a6bb39e` | MIT | Pass | Adopted with edits |
| `playwright-cli` | microsoft/playwright-cli | `c872a33c` | Apache-2.0 | Pass (caveats), fixed | Adopted with edits |
| `tdd` | mattpocock/skills `engineering/tdd` | `abeeaf95` | MIT | Pass | Adopted with edits |
| `langchain-rag` | langchain-ai/langchain-skills | — | — | — | Not adopted: removed upstream; LangChain docs come from Context7 |
| `claude-api` | built into Claude Code | — | — | — | Not vendored |

No skill contained prompt injection, invisible characters or encoded payloads. The findings
below are about execution, supply chain and fit.

## Notable findings

**shadcn: auto-executed command.** `SKILL.md` used dynamic context injection
(`` !`npx shadcn@latest info --json` ``), which runs the latest npm release of the CLI as soon
as the skill loads, before any approval. `allowed-tools` also pre-approved every
`shadcn@latest` subcommand (`add <url>`, `init --force`, `apply`, `mcp init`). Both were
removed. CLI commands are now proposed to the user and use the version pinned in
`frontend/package.json`. Community registries, automatic doc fetching, presets, OKLCH colors
and dark mode were removed (the project uses hex tokens and a light theme only).

**playwright-cli: tool pre-approval and credential exposure.** `allowed-tools` pre-approved
`npx playwright:*` and `run-code` (arbitrary JavaScript). The skill also documented attaching to
the user's real browser (`attach --extension`, `--cdp`), saving auth state and cookies to the
working directory, literal passwords, global `@latest` installs and uploading screenshots and
videos to PRs. All of these were removed or constrained. Auth state, traces and reports are
gitignored because they can contain tokens.

**modern-python: not vendored.** The plugin ships a `SessionStart` hook that prepends
`python`/`pip`/`uv` shims to `PATH` for the whole session. The code is not malicious, but it
silently changes the environment. The skill standardises on `ty` (this project uses mypy
strict), runs `uv add` and deletes `.venv` without asking, and suggests `curl | sh`
installers. It is licensed CC BY-SA 4.0, so a modified copy would have to stay share-alike.
A short original `python-tooling` skill replaces it.

**Fit edits.** Every other change (Next.js/SSR content removed, `ty` replaced by mypy strict,
async-first FastAPI, Supabase/Timescale specifics removed, pool-safe `SET LOCAL`, MSW for network
mocking, red → green → refactor) is listed per skill in its `SOURCE.md` under *Modifications*.

## Re-curation

Updating a skill means fetching the new upstream commit, diffing it against the `SOURCE.md`
commit, repeating the five checks on the diff and updating `SOURCE.md` and this table.

## MCP servers

`.mcp.json` pins `postgres-mcp` to an exact version in `restricted` (read-only) mode and reads
its DSN from `CWYD_MCP_DATABASE_URI` (a read-only role; credentials are never committed).
Context7 is the vendor-hosted HTTP endpoint, so it is not pinned; it only returns public
library documentation. Bump either deliberately, never to `@latest`. `uvx` resolves
`postgres-mcp`'s transitive dependencies at run time (not locked); accepted for a dev-only,
read-only server.
