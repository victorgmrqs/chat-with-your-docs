---
paths:
  - "backend/**/*.py"
---

# Backend architecture (ports and adapters)

- Layers: `domain` (entities, value objects, rules) → `application` (use cases, ports) →
  `adapters` (LLM, embeddings, Postgres, parsers) → `api` (FastAPI routers, DTOs).
  Imports point inward only; `domain` and `application` never import FastAPI, LangChain,
  SQLAlchemy, provider SDKs or `os.environ`.
- Tracing exception: `application` may import only the vendor-neutral OpenTelemetry API
  (`opentelemetry.trace` and its types, a no-op without an SDK); span/attribute names and the
  span helpers come from `app/application/telemetry.py`. The OpenTelemetry SDK and exporters
  (`opentelemetry.sdk`, `opentelemetry.exporter.*`) live only in `app/adapters/telemetry.py`;
  `domain` imports no OpenTelemetry at all.
- Ports are `typing.Protocol` classes in `application`: `ChatModelPort`, `EmbeddingPort`,
  `DocumentRepository`, `RetrieverPort`, `DocumentParserPort`. Adapters implement them.
  Model calls return `Generation(value, usage)` so the use case records tokens (DOM-24).
- Routes are thin: validate the request DTO, call one use case obtained through `Depends`,
  map the result to a response DTO. No SQL, LangChain or SDK calls in routers.
  Exception: infrastructure probes (`/health*`) have no business logic and call their adapter
  (`container.readiness`) directly; they still go through `Depends` and never touch SQL.
- Wiring lives in a single composition root (`app/composition.py`): settings,
  engine, adapters, use cases. Model names, providers and flags (`RERANK_ENABLED`) come from
  settings (pydantic-settings), never hardcoded.
- `build_container(settings)` returns a frozen, slotted `Container` dataclass. `create_app`
  builds it inside the `lifespan` (settings are loaded there, never at import), stores it on
  `app.state.container` and disposes the engine on shutdown. Routes reach it only through
  `Depends(get_container)`; nothing else reads `app.state`.
- New settings go in `app/config.py` and in `.env.example` + `docs/operations.md` (configuration table) in the same change.
- Async first: `async def` everywhere I/O happens; blocking SDK or parsing calls run in
  `asyncio.to_thread` inside the adapter.
- Background indexing jobs get their own resources from the composition root; they never reuse
  request-scoped dependencies.
- Errors: domain raises typed exceptions (`DocumentNotFound`, `UnsupportedFormat`,
  `InsufficientEvidence`…); one exception handler maps them to HTTP status and a stable error
  code. Never leak stack traces or provider messages to clients.
- Observability: one span per real pipeline step (no span for work that is not a separate
  call, e.g. the parts of one SQL statement), opened with `telemetry.step`; span and attribute
  names only from `app/application/telemetry.py`. Attributes carry sizes, counts, scores, ids,
  model names and token usage, never question, prompt, chunk or answer text; that text goes
  only to span events via `add_content`, gated by `CAPTURE_CONTENT` (DOM-22). Failures record
  error status and `error.type`, never the exception message or stack trace.
- Typing: mypy strict must pass; no `Any` in public signatures; no `# type: ignore` without a
  reason comment.
