# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Every entry links its Jira card.

## [Unreleased]

### Added

- Monorepo scaffold (React + Vite, FastAPI with uv) and a one-command local stack: `docker compose up
  --build --wait` starts PostgreSQL + pgvector, the API and the web app, each gated on a health
  check (`/health`, `/health/ready`); startup fails fast naming every missing configuration variable;
  one command each for lint, typecheck and test
  ([CWYD-2](https://goncalvesmarques.atlassian.net/browse/CWYD-2)).
- Document upload and background indexing with chunk provenance and Indexing/Ready/Failed status:
  `POST /documents` accepts `.pdf`, `.md` and `.txt` up to `MAX_UPLOAD_MB`, re-uploading the same
  file returns the existing document, and failures say whether to upload another version or retry
  ([CWYD-3](https://goncalvesmarques.atlassian.net/browse/CWYD-3)).
- Questions answered from the owner's Ready documents with verifiable citations, or an explicit
  "Not enough evidence": `POST /chat` returns numbered sources (file, page or heading, passage)
  built from the stored chunks, never confuses a provider timeout or error with missing evidence
  (`504 chat_timeout`, `502 chat_unavailable`), and runs on OpenAI or Anthropic by configuration
  (`CHAT_PROVIDER`), with an optional reranker (`RERANK_ENABLED`); the sampling temperature is
  the provider's default unless `CHAT_TEMPERATURE` is set, since some models reject it
  ([CWYD-4](https://goncalvesmarques.atlassian.net/browse/CWYD-4)).

### Maintenance

- AI-assisted development foundation: workflow configuration, path-scoped rules, 10 curated and
  security-reviewed skills plus 1 original, read-only Postgres and Context7 MCP servers, and protected
  `main`/`development` branches ([CWYD-9](https://goncalvesmarques.atlassian.net/browse/CWYD-9)).
