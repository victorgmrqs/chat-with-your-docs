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
- Offline RAG evaluation: a golden dataset over the fixture documents and one command
  (`docker compose --profile eval run --build --rm eval`) that reports hit@k, MRR, correct refusals,
  citation validity, latency and chat cost per configuration; the committed comparison keeps the
  defaults (reranker off, 1000/150 chunks, `MIN_RELEVANCE` 0.30)
  ([CWYD-11](https://goncalvesmarques.atlassian.net/browse/CWYD-11)).
- Design system and UI components from the design handoff: design tokens with a drift audit
  (`npm run tokens:audit`), a light Tailwind theme with Inter and the brand icon, and the document
  sidebar, chat thread, answer with numbered sources, loading, error and "Not enough evidence"
  states, composed into the five handoff screens on a dev-only preview page
  ([CWYD-10](https://goncalvesmarques.atlassian.net/browse/CWYD-10)).
- The screen now uploads documents, tracks indexing, asks questions and shows citations through
  the real API: statuses refresh every 2 s while a document is indexing, a failed question stays
  in the thread with Retry only for transient failures, and the client is typed from the API's
  OpenAPI schema (`npm run api:types`); `VITE_API_MOCKS=true npm run dev` runs the app without
  the backend. The sidebar stays fixed while the conversation scrolls, the list shows a loading
  state instead of looking empty, and focus is a solid, visible outline
  ([CWYD-5](https://goncalvesmarques.atlassian.net/browse/CWYD-5)).
- Continuous integration on every pull request: backend and frontend checks run only for the
  component a change touches, both Docker images are built and scanned for fixable HIGH/CRITICAL
  vulnerabilities, and a single always-reporting `ci-gate` is the required check. Pushes to
  `development`/`main` and version tags publish both images to GHCR, tagged `sha-<commit>` and
  identified by digest, only when every check and scan passed. Both images now pass that scan:
  the backend drops the unused system pip and the frontend moves to mainline nginx 1.31
  ([CWYD-6](https://goncalvesmarques.atlassian.net/browse/CWYD-6)).
- OpenTelemetry traces for chat and ingestion: one trace per request, rooted at FastAPI's HTTP
  span, with a pipeline span per question (`rag.chat`) and per indexing run (`ingest.document`)
  and a span per step (`/health*` probes are not traced), token usage per model and an estimated
  cost from a price table shared with the RAG evaluation, and no question, prompt, chunk or
  answer text unless `CAPTURE_CONTENT=true`. Exporter by `OTEL_TRACES_EXPORTER`
  (`none` by default, `console`, `otlp`); Jaeger runs under the Compose `observability` profile.
  Every response carries `X-Request-ID`, error bodies carry the same `request_id`, and an
  unexpected failure answers `500 internal_error`
  ([CWYD-12](https://goncalvesmarques.atlassian.net/browse/CWYD-12)).

### Security

- Every web server response, errors included, carries `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: strict-origin-when-cross-origin` and `X-Frame-Options: DENY`; the app also
  gets a same-origin `Content-Security-Policy`, while `/api/` responses (JSON, Swagger UI) do not.
  `API_DOCS_ENABLED=false` (default `true`; production sets it) makes `/docs`, `/redoc` and
  `/openapi.json` return `404`
  ([CWYD-14](https://goncalvesmarques.atlassian.net/browse/CWYD-14)).

### Maintenance

- AI-assisted development foundation: workflow configuration, path-scoped rules, 10 curated and
  security-reviewed skills plus 1 original, read-only Postgres and Context7 MCP servers, and protected
  `main`/`development` branches ([CWYD-9](https://goncalvesmarques.atlassian.net/browse/CWYD-9)).
- Autonomous sprint loop (`/loop /sprint`, dev-workflow 0.8.0) for cards labelled `auto-ok`: every
  merge to `development` needs the `ci-gate` check and an approval from a second reviewer from
  another vendor (agy, blocking); `scripts/loop/` holds the launcher and the loop's permission denies
  ([CWYD-25](https://goncalvesmarques.atlassian.net/browse/CWYD-25)).
- Security review skills and rules for agents: `owasp-security` (OWASP Top 10, ASVS, LLM Top 10)
  and a read-only `differential-review` (git history, blast radius), both pinned and security-reviewed
  copies, plus path-scoped rules for nginx headers and limits, upload validation and LLM/RAG code
  ([CWYD-17](https://goncalvesmarques.atlassian.net/browse/CWYD-17)).
