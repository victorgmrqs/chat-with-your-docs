# CLAUDE.md — Chat With Your Docs

<!-- Max 80 lines. Facts only. Procedures live in skills; layer conventions in rules.
     AGENTS.md is a symlink to this file. -->

## Overview

Upload documents (.pdf, .md, .txt), ask questions in natural language and get answers
grounded in those documents with verifiable citations, or an explicit "not enough
evidence". Take-home challenge for NewPage Solutions (AI Forward Deployed Engineer).
Architecture: React SPA → FastAPI → PostgreSQL + pgvector, LLMs behind ports/adapters.

## Stack

- Frontend: React + Vite + TypeScript, Tailwind v4 + shadcn/ui (`frontend/`)
- Backend: Python, FastAPI + LangChain v1, uv + ruff + mypy strict (`backend/`)
- Database: PostgreSQL + pgvector (hybrid search: vector + full-text, RRF)
- LLM: `ChatModelPort` (OpenAI, Anthropic adapters); `EmbeddingPort` (OpenAI)
- Tests: pytest (real Postgres via testcontainers), Vitest + Testing Library + MSW, Playwright
- Runtime: Docker Compose is the main validation path

## Commands

```bash
docker compose up --build --wait   # full stack: web :8080, API :8000, db :5432
# lint / typecheck / test (dev container): `commands` in .dev-workflow/workflow.config.yaml;
# per component: backend/CLAUDE.md, frontend/CLAUDE.md
```

## Non-negotiable constraints

- English only in every artifact: code, comments, docs, tickets, commits.
- Domain and use cases never import a provider SDK; model names come from configuration.
- Answers cite only chunks that were retrieved; invented chunk IDs are dropped.
- Retrieval filters (owner, Ready status) are set by the app, never by the LLM.
- Question, prompt, chunk and answer content never goes to logs or span attributes.
- Integration tests use real PostgreSQL, never SQLite; LLM/embeddings use declared fakes.
- Frontend uses design tokens only; red is reserved for failures.
- Secrets only via environment; `.env.example` holds no secrets.
- Never install, upgrade or remove packages, run one-off tools (`npx`, `uvx`) or delete files
  without asking the user.

## Workflow

- Tickets: Jira project CWYD (board 138). Execution: `/task CWYD-N` → brief → approval →
  implementation/tests → `/docs-sync` → DoD → `/simplify` → `/code-review-task` → delivery.
- Branches: `feat/CWYD-N-slug` from `development`; release merges `development` → `main`.
  `main` and `development` are protected (PR only, no force push, no deletion); merged feature
  branches are deleted automatically. Never push to them, never `--force`, never `--no-verify`.
  Merge methods: feature → `development` squash only; release `development` → `main` merge
  commit only, then tag `vX.Y.Z` on `main`.
- Configuration: `.dev-workflow/workflow.config.yaml`.
- Commits and PRs follow `{type}(CWYD-N): message` and never mention AI assistance:
  no agent `Co-Authored-By` trailer and no `Generated with …` line.
- Every task adds a `CHANGELOG.md` [Unreleased] entry linking the card.

## Rules and skills

- `.claude/rules/` are path-scoped. `.claude/skills/` are pinned, edited third-party copies
  (curation and security review: `docs/skills-curation.md`); this file, the rules and each
  skill's "Project overrides" win over upstream skill text.
- MCP (`.mcp.json`, versions pinned there): read-only Postgres for local dev, Context7 for
  current library docs. Prefer Context7 over memory for LangChain, FastAPI, Vite and shadcn.

## Documentation (read on demand)

- Working guide and decision log (local, untracked): `_docs/playbook.md`, `_docs/decision-log.md`
- Challenge statement: `_docs/challenge.md`
- Design handoff: `_docs/design/` (PNGs win over `.dc.html` on divergence)
- RAG eval reports: `docs/eval/` · HTTP evidence: `docs/http/`
