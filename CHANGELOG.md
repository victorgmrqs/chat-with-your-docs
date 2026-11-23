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
- Ingestion refuses work it cannot finish: an `EMBEDDING_DIMENSIONS` that differs from the
  database's `vector` column fails readiness and uploads (`503 embedding_dimension_mismatch`,
  nothing stored) and is logged once at startup, instead of failing every upload as retryable;
  the API itself cuts off request bodies over `MAX_UPLOAD_MB` plus 1 MB with `413 file_too_large`
  (not only nginx); a Ready transition from any state other than `indexing` writes no chunks; and a
  rejected embeddings API key or model ends `provider_misconfigured`, retryable by re-upload once
  the operator fixes it, with Retry offered in the UI (documents now carry `can_retry`). The README
  shows the `DEFAULT_OWNER_ID` default ([CWYD-16](https://goncalvesmarques.atlassian.net/browse/CWYD-16)).
- The web server rate-limits questions and uploads per client address (questions 10 per minute,
  burst 5, at most 2 at a time; uploads 6 per minute, burst 3; listing and polling stay free):
  requests over a limit get `429 rate_limited` with `Retry-After: 60`, shown in the app without
  Retry, and the limits are tunable with `RATE_LIMIT_*` in `.env`
  ([CWYD-18](https://goncalvesmarques.atlassian.net/browse/CWYD-18)).
- Uploads whose content does not match the extension (a `.pdf` not starting with `%PDF-`, a
  `.md` or `.txt` that is not valid UTF-8 or contains NUL bytes) are rejected with
  `415 unsupported_type` before anything is stored, and PDF parsing has a budget: a PDF over
  `PDF_MAX_PAGES` (default 500) or `PDF_PARSE_TIMEOUT_SECONDS` (default 60) ends `failed` with the
  permanent reason `too_many_pages` or `parse_timeout`, each with a message saying what to upload
  instead ([CWYD-19](https://goncalvesmarques.atlassian.net/browse/CWYD-19)).
- The web server no longer shows its version and sends a deny-all `Permissions-Policy` (camera,
  microphone, geolocation, payment, usb) on every response, errors included; Swagger UI now works
  through it at `/api/docs` (spec at `/api/openapi.json`, "Try it out" included) as well as directly
  on the API at `/docs`, since the API honours `X-Forwarded-Prefix` only when it equals
  `API_ROOT_PATH` (default `/api`) ([CWYD-20](https://goncalvesmarques.atlassian.net/browse/CWYD-20)).
- Instructions written inside an uploaded document (override the rules, reveal the prompt, cite
  another file, hidden PDF text) are never followed nor counted as evidence (DOM-29), and an
  adversarial prompt-injection set (8 cases over 8 fictitious documents, own evaluation owner so
  the golden metrics stay comparable) now runs with every evaluation and is reported in its own
  section; the regression tolerance is documented in `docs/eval/README.md`
  ([CWYD-21](https://goncalvesmarques.atlassian.net/browse/CWYD-21)).

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
- Readiness check failure paths are tested against real PostgreSQL (timeout, dropped connection,
  SQL errors propagating), every pytest fixture lives in `tests/conftest.py`, and `.env.example`
  separates the Compose `POSTGRES_*` block from the outside-Compose `DATABASE_URL`
  ([CWYD-13](https://goncalvesmarques.atlassian.net/browse/CWYD-13)).
