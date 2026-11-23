# Source

- Upstream: https://github.com/agamm/claude-code-owasp (author: Agam More)
- Path: `.claude/skills/owasp-security`
- Commit: 1ae29cb22518560e3625d77f2ae64f61647d9201
- License: MIT (see `LICENSE`)
- Vendored: 2026-11-22 (CWYD-17)
- Modified: yes

## Modifications

- Frontmatter: added `license`; trimmed `when_to_use` (dropped "secrets in code", "supply chain"
  and "harden this Dockerfile or workflow", covered by the rules); added `## Project overrides`.
- `SKILL.md`: removed the four references to `reference/owasp-report.md`. The LLM step points to
  the checklist's "LLM and Agent Features" section and `.claude/rules/security-llm.md`, and the
  L3 note points to the ASVS 5.0 standard. The Agentic Top 10 and ASVS 5.0 sections moved
  unchanged to `reference/standards.md` (loaded on demand); the auth-middleware hint names
  FastAPI dependencies instead of Next.js/Express/Django/Rails.
- `reference/languages.md`: kept JavaScript / TypeScript, Python, Shell (Bash) and SQL; removed
  the other 16 languages and their contents entries.
- `reference/config-and-supply-chain.md`: removed "A02: Kubernetes" and "A02: Cloud &
  Terraform" with their contents entries, and the Yarn, pnpm, Poetry, Go, Rust, Gradle and
  Maven rows of the lockfile table.
- `reference/review-checklist.md`: unchanged.

## Dropped files

- `reference/owasp-report.md` (about 1100 lines; read upstream when needed)
- Repository files outside the skill: `evals/`, `scripts/test-graders.mjs`, `.claude-plugin/`
