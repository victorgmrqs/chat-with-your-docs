# Operations reference

Configuration, API behaviour, tracing, security headers, rate limits and troubleshooting for the
Compose stack. Setup and the design rationale are in the [README](../README.md).

## Configuration

Every variable is listed in [`.env.example`](../.env.example).

| Variable            | Required                       | Purpose                                         |
| ------------------- | ------------------------------ | ----------------------------------------------- |
| `CHAT_PROVIDER`     | yes                            | `openai` or `anthropic`                         |
| `CHAT_MODEL`        | yes                            | Chat model name for the selected provider       |
| `EMBEDDING_MODEL`   | yes                            | OpenAI embedding model                          |
| `OPENAI_API_KEY`    | yes                            | Embeddings always use OpenAI                    |
| `ANTHROPIC_API_KEY` | when `CHAT_PROVIDER=anthropic` | Anthropic chat model                            |
| `POSTGRES_*`        | no                             | Local database credentials (default `cwyd`)     |
| `MAX_UPLOAD_MB`     | no (10)                        | Upload size limit; larger files get `413`       |
| `PDF_MAX_PAGES`     | no (500)                       | PDFs with more pages fail with `too_many_pages` |
| `PDF_PARSE_TIMEOUT_SECONDS` | no (60)                | Longer PDF parses fail with `parse_timeout`     |
| `RATE_LIMIT_*`      | no                             | Web server rate limits, see [Rate limits](#rate-limits) |
| `EMBEDDING_DIMENSIONS` | no (1536)                   | Must match the `vector` column of the migration; a mismatch fails readiness and uploads (`503`) |
| `CHUNK_SIZE`        | no (1000)                      | Chunk size in characters                        |
| `CHUNK_OVERLAP`     | no (150)                       | Overlap between chunks; smaller than the size   |
| `DEFAULT_OWNER_ID`  | no (`00000000-0000-0000-0000-000000000001`) | Owner of every document (single-user MVP) |
| `QUESTION_MAX_CHARS` | no (2000)                     | Longer questions get `400 question_too_long`    |
| `RETRIEVAL_CANDIDATES` | no (20)                     | Chunks per search branch (vector, full-text)    |
| `RETRIEVAL_TOP_K`   | no (6)                         | Fused chunks considered for the prompt; at most twice `RETRIEVAL_CANDIDATES` |
| `MIN_RELEVANCE`     | no (0.30)                      | Cosine floor (0-1) for vector-only hits         |
| `RERANK_ENABLED`    | no (false)                     | One extra chat call that reranks the evidence   |
| `RERANK_TOP_N`      | no (4)                         | Chunks kept by the reranker                     |
| `CONTEXT_TOKEN_BUDGET` | no (3000)                   | Token budget of the sources in the prompt       |
| `ANSWER_MAX_TOKENS` | no (800)                       | Maximum answer length in tokens                 |
| `CHAT_TIMEOUT_SECONDS` | no (30)                     | Per-attempt chat provider timeout               |
| `CHAT_MAX_RETRIES`  | no (2)                         | Retries on timeouts, 429 and 5xx                |
| `CHAT_TEMPERATURE`  | no (unset)                     | Sent only when set; some models reject it       |
| `OTEL_TRACES_EXPORTER` | no (`none`)                 | Tracing: `none`, `console` (stdout) or `otlp` (Jaeger) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | no (Compose: `http://jaeger:4318`) | OTLP/HTTP base URL; `/v1/traces` is added. Jaeger's OTLP port is not published, so `otlp` reaches it only from inside Compose |
| `OTEL_SERVICE_NAME` | no (`cwyd-backend`)            | Service name shown in Jaeger                    |
| `OTEL_TRACES_SAMPLER_ARG` | no (1.0)                 | Share of new traces kept (0-1)                  |
| `CAPTURE_CONTENT`   | no (false)                     | Dev only: question, prompt and answer text as span events |
| `PRICE_TABLE_PATH`  | no (bundled `app/prices.yaml`) | Chat and embedding model prices for the estimated cost; a relative value resolves from the working directory |
| `API_DOCS_ENABLED`  | no (true)                      | `false` removes `/docs`, `/redoc` and `/openapi.json` (404); set it in production |
| `API_ROOT_PATH`     | no (/api)                      | Prefix the web server proxies to the API; must match its `X-Forwarded-Prefix` |
| `EVAL_UID`, `EVAL_GID` | no (1000)                   | Host user that writes the RAG evaluation reports |

`DATABASE_URL` is built by Compose from the `POSTGRES_*` values. Set it yourself only when
running the API outside Compose (scheme `postgresql+asyncpg://`; other schemes are rejected at
startup). Keep `POSTGRES_*` URL-safe (letters, digits, `-`, `_`, `.`): they are inserted into
the URL as is.

`POSTGRES_*` take effect only when the database volume is created. After changing them, recreate
it with `docker compose down -v` (this deletes the local data), or the backend keeps failing
authentication against the old credentials.

## Health check

```bash
curl -s localhost:8000/health         # {"status":"ok"}  liveness, never touches the database
curl -s localhost:8000/health/ready   # {"status":"ready","pgvector":"0.8.7"}
curl -s localhost:8080/api/health     # same API through the frontend's nginx proxy
```

`/health/ready` answers `503` with `database unavailable` or `pgvector extension missing` when
the dependency is not there, and with `embedding dimension mismatch` when `EMBEDDING_DIMENSIONS`
differs from the database's `vector` column (also logged once at startup). Compose uses it as
the backend health check, and the frontend only starts once the backend is ready.

## Documents

Upload `.pdf` (with selectable text), `.md` or `.txt` files up to `MAX_UPLOAD_MB`. The content
must match the extension (a `.pdf` starts with `%PDF-`, text is UTF-8 without NUL bytes),
otherwise `415`. Indexing
runs in the background: the upload answers `202` with status `indexing`; poll until `ready` or
`failed`. A PDF over `PDF_MAX_PAGES` or `PDF_PARSE_TIMEOUT_SECONDS` fails with `too_many_pages`
or `parse_timeout` (DOM-28).

```bash
curl -s -F file=@backend/tests/fixtures/documents/expense-policy.pdf localhost:8000/documents
curl -s localhost:8000/documents/<id>   # {"status":"ready","chunk_count":N,...}
curl -s localhost:8000/documents        # all documents, newest first
```

- Uploading the same file again returns the existing document (`200`) instead of a copy. A
  document that failed with `indexing_failed` (temporary: embeddings provider or database
  unavailable) or `provider_misconfigured` (the provider rejected `OPENAI_API_KEY` or
  `EMBEDDING_MODEL`: fix the setting first) is indexed again on re-upload (`202`, same id);
  `no_extractable_text` (for example a scanned PDF) needs another version of the file. Each
  document's `can_retry` says which case applies (DOM-04).
- Errors use one envelope, `{"code": "...", "detail": "...", "request_id": "..."}`:
  `415 unsupported_type`, `413 file_too_large`, `400 empty_file`, `404 document_not_found`,
  `503 database_unavailable`, `503 embedding_dimension_mismatch`, and `500 internal_error` with
  a generic message for any unexpected failure. `request_id` equals the `X-Request-ID` header
  every response carries; quote it when reporting a problem (see [Tracing](#tracing)). Through the frontend proxy
  (`:8080/api`), nginx accepts bodies up to 11 MB (10 MB plus multipart overhead) and answers
  larger ones with `413 file_too_large` (`code` and `detail` only: the request never reaches the
  API, so there is no `request_id` or trace); raise `client_max_body_size` in
  `frontend/nginx/default.conf.template` together with `MAX_UPLOAD_MB`. Called directly
  (`:8000`), the API itself cuts off bodies over `MAX_UPLOAD_MB` plus 1 MB without reading them
  (`413 file_too_large` with `request_id`).
- A document left `indexing` by a restart is marked `failed` / `indexing_failed` when the API
  starts; upload it again to retry.
- Every request in [`docs/http/documents.http`](http/documents.http) can be run against the
  Compose stack. Business rules: [`docs/domain-context.md`](domain-context.md) (DOM-01..06, DOM-25..26).

## Chat

Ask a question about the Ready documents. The answer cites its sources with `[n]` markers, or
says "Not enough evidence" when the documents do not support one.

```bash
curl -s localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"question": "What is the monthly coworking reimbursement limit?"}'
# {"outcome":"answered","answer":"... US$ 250 per month [1].","sources":[{"number":1,
#   "filename":"expense-policy.pdf","page":2,"passage":"..."}],"provider":"openai",...}
```

- Retrieval is hybrid, in PostgreSQL: vector search (pgvector, cosine) and full-text search
  (any of the question's terms) fused with Reciprocal Rank Fusion, limited to the owner's Ready
  documents. A chunk counts as evidence only if it matched the full-text search or its cosine
  similarity is at least `MIN_RELEVANCE`; with no evidence the chat model is not called.
- With `RERANK_ENABLED=true` one extra chat call keeps the `RERANK_TOP_N` most relevant chunks;
  if it fails, the fused order is used and the response says `"reranked": false`.
- Sources reach the prompt labelled `S1..Sn`, delimited and escaped, within
  `CONTEXT_TOKEN_BUDGET`. The model cites labels; the backend drops labels that were not in the
  prompt, renumbers the rest `1..n` and builds each source (file, page or heading, passage) from
  the stored chunk. An answer with no valid citation becomes `insufficient_evidence`.
- `outcome: "insufficient_evidence"` is a normal `200`: the answer is a fixed message, `sources`
  is empty and `related_passage` may show the closest passage, without a citation number.
- Errors: `400 empty_question`, `400 question_too_long`, `409 no_ready_documents`,
  `502 chat_unavailable` (provider error or invalid structured output), `502
  retrieval_unavailable` (the question could not be embedded), `504 chat_timeout`,
  `503 database_unavailable`. Provider failures are never reported as insufficient evidence.
- `CHAT_PROVIDER` (`openai` or `anthropic`) and `CHAT_MODEL` select the chat model; every
  response carries `provider` and `model`. Logs and traces record outcome, counts, timings,
  provider, model and tokens, never the question, prompt, sources or answer.
- Chat calls go through LangChain; embeddings call the OpenAI SDK's `embeddings.create`
  directly, because LangChain's `OpenAIEmbeddings` drops the token usage the cost needs
  ([CWYD-28](https://goncalvesmarques.atlassian.net/browse/CWYD-28)).
- Every request in [`docs/http/chat.http`](http/chat.http) can be run against the Compose
  stack; the expected evidence per case is in
  [`backend/tests/fixtures/rag_cases.json`](../backend/tests/fixtures/rag_cases.json). Business
  rules: [`docs/domain-context.md`](domain-context.md) (DOM-07..13).

## Database schema

Tables and indexes are created by Alembic migrations (`backend/migrations/`). The backend
container runs `alembic upgrade head` before starting the API; if the migration fails, the
container exits instead of serving an outdated schema (`docker compose logs backend`). Outside
Compose, run it yourself from `backend/`:

```bash
uv run --env-file ../.env alembic upgrade head   # needs DATABASE_URL
```

The `vector` column size is fixed by the migration (1536) and must match `EMBEDDING_DIMENSIONS`.
Changing `EMBEDDING_MODEL` or `EMBEDDING_DIMENSIONS` does not re-embed existing chunks, and
re-uploading an indexed file returns it unchanged: recreate the database with
`docker compose down -v` (a dimension change also needs a new migration) and upload the
documents again.

## Tracing

The API emits OpenTelemetry traces, off by default (`OTEL_TRACES_EXPORTER=none`). To see them in
Jaeger, set `OTEL_TRACES_EXPORTER=otlp` in `.env` and start the stack with the `observability`
profile:

```bash
docker compose --profile observability up --build --wait   # Jaeger UI on http://localhost:16686
```

`OTEL_TRACES_EXPORTER=console` prints the spans to the backend's stdout instead
(`docker compose logs backend`), with no extra service. Jaeger keeps traces in memory: they are
lost when it restarts. Its OTLP receiver is reachable only from the Compose network.

| Trace | Spans | Find it in Jaeger (service `cwyd-backend`) |
| --- | --- | --- |
| Question | `POST /chat` → `fastapi.endpoint` → `rag.chat` → `retrieval.embed_query`, `retrieval.hybrid`, `rerank` (with `RERANK_ENABLED`), `answer_generation` | Tag `app.request_id=<X-Request-ID of the response>` |
| Ingestion | `POST /documents` → `fastapi.background_task` → `ingest.document` → `ingest.parse`, `ingest.chunk`, `ingest.embed`, `ingest.store` | Tag `app.document.id=<document id>` |

- The trace root is the HTTP request span that FastAPI's native telemetry adds (route, status
  code, total latency, plus `fastapi.*` operation spans); `rag.chat` and `ingest.document` are the
  pipeline spans inside it. Indexing runs after the `202`, in the upload request's trace.
  `/health*` probes are not traced. A client's `traceparent`, `tracestate` and `baggage` headers
  are ignored: every request starts its own trace (`X-Request-ID` is the correlation key), and
  FastAPI's telemetry exports no logs.
- With `CHAT_PROVIDER=anthropic`, the Anthropic SDK adds its own `anthropic.messages.create`
  spans under `rerank` and `answer_generation` (metadata only by default; they include the
  Anthropic organization and workspace ids). Never set
  `ANTHROPIC_OPEN_TELEMETRY_TRACES_CONTENT_MODE=content`: it would put prompts and answers on
  those spans, bypassing `CAPTURE_CONTENT`.
- Retrieval is one span: vector search, full-text search and the fusion run as a single SQL
  statement, so its counts (returned, full-text matched, top similarity) are attributes of
  `retrieval.hybrid`.
- `rag.chat` records `app.outcome` (`answered`, `refused` or `error`), provider and
  model, input/output tokens and `app.cost.usd`, the estimated cost from
  [`backend/app/prices.yaml`](../backend/app/prices.yaml) (USD per million tokens, matched by
  model-name prefix). The totals include the query embedding (`retrieval.embed_query` records its
  model and tokens). A model missing from the table records no cost; a question where no call
  reported usage records no tokens and no cost, never 0. The RAG evaluation reads the same table.
- `ingest.embed` records the embedding model, input tokens and `app.cost.usd` of an indexing
  job, and a successful job logs one info line with the document id, chunk count, embedding
  tokens and estimated cost (null when unknown).
- A failed step has error status and `error.type` (the exception class), never the exception
  message or stack trace.
- Span attributes never carry question, prompt, chunk or answer text. `CAPTURE_CONTENT=true` adds
  that text as span events for local debugging; keep it `false` anywhere real documents are used.
- Every request in [`docs/http/observability.http`](http/observability.http) produces one of
  these traces; screenshots of each are in [`docs/evidence/CWYD-12/`](evidence/CWYD-12/).
  Business rules: [`docs/domain-context.md`](domain-context.md) (DOM-22..24).

## Security headers

The web server ([`frontend/nginx/default.conf.template`](../frontend/nginx/default.conf.template)) sends
`X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin` and
`X-Frame-Options: DENY` and `Permissions-Policy: camera=(), microphone=(), geolocation=(),
payment=(), usb=()` on every response, errors included, and does not announce its version
(`Server: nginx`). The app itself also gets a
`Content-Security-Policy` that allows only same-origin scripts, styles, fonts and requests and
forbids framing. API responses under `/api/` do not: JSON needs no CSP, and it would block
Swagger UI's inline script and CDN assets. HSTS is set by the ingress that ends TLS (CWYD-7).
Check the headers with `curl -I http://localhost:8080/`
([`docs/http/security.http`](http/security.http)).

The API docs (`/docs`, `/redoc`, `/openapi.json`) are on by default for local and homolog use.
Production sets `API_DOCS_ENABLED=false`, which makes the three routes return `404`; the
committed `frontend/openapi.json` export does not depend on them. Swagger UI works both
through the web server (`http://localhost:8080/api/docs`, the only entry point in homolog) and
directly (`http://localhost:8000/docs`): nginx sends `X-Forwarded-Prefix: /api`, and when it
equals `API_ROOT_PATH` the API serves the page and spec as seen from the browser
(`/api/openapi.json`, `servers: [{"url": "/api"}]`), so "Try it out" calls `/api/...`. Any other
value of the header is ignored. Direct calls carry no header and keep the plain paths.

## Rate limits

The web server limits each client address (DOM-27): questions (`POST /api/chat`) to 10 per
minute with a burst of 5 and at most 2 at a time, uploads (`POST /api/documents`) to 6 per minute
with a burst of 3. Listing and polling documents is not limited. A request over a limit gets
`429` with `{"code":"rate_limited","detail":"Too many requests. Try again in a minute."}`, a
`Retry-After: 60` header and the security headers above; the app shows the message. Direct calls
to the API (`:8000`) are not limited.

Change them in `.env` and restart the web server (`docker compose up -d frontend`):

| Variable | Default | Meaning |
|---|---|---|
| `RATE_LIMIT_CHAT` | `10r/m` | Questions per client address (nginx rate: `r/s` or `r/m`) |
| `RATE_LIMIT_CHAT_BURST` | `5` | Extra questions let through at once before the rate applies |
| `RATE_LIMIT_CHAT_CONNECTIONS` | `2` | Questions in progress at the same time |
| `RATE_LIMIT_UPLOAD` | `6r/m` | Uploads per client address |
| `RATE_LIMIT_UPLOAD_BURST` | `3` | Extra uploads let through at once |

The key is the address nginx sees. Behind an ingress or load balancer (CWYD-7; `real_ip` is
CWYD-20) that is the
proxy, so every user shares one limit: the web server then needs `real_ip_header
X-Forwarded-For` with `set_real_ip_from` listing only the trusted proxy CIDRs (never
`0.0.0.0/0`, or clients can spoof the header). That is not configured here. Requests in
[`docs/http/rate-limit.http`](http/rate-limit.http); real output in
[`docs/evidence/CWYD-18-rate-limit.md`](evidence/CWYD-18-rate-limit.md).

## Troubleshooting

**`docker compose up --wait` fails and the backend exits with `Invalid configuration`.**
The API validates its configuration at startup and names every variable that is missing or
empty:

```
app.config.ConfigurationError: Invalid configuration:
  - CHAT_MODEL: Field required
  - OPENAI_API_KEY: Field required
Set these variables in .env (see .env.example) and restart.
```

Fill in the listed variables in `.env` and run `docker compose up --build --wait` again.
`docker compose logs backend` shows the message after the fact.

**A value in `.env` is not picked up as expected.** Compose does not strip inline comments in
env files: `CHAT_PROVIDER=openai # note` sets the whole string. Keep comments on their own lines.

**`ports are not available` for 5432, 8000 or 8080.** Another process (a local PostgreSQL, an
editor port forward) holds the port. Stop it, or change the host side of the mapping in
`compose.yaml`.

**The backend exits right after start with an Alembic error.** The schema migration runs before
the API and failed (database unreachable, or a schema changed by hand). `docker compose logs
backend` shows the cause; for a local database you do not need to keep, `docker compose down -v`
and start again.

**`pgvector extension missing` after editing `db/init/`.** Init scripts run only on an empty
volume. Recreate it with `docker compose down -v`.
