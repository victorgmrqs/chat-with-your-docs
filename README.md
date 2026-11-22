# Chat With Your Docs

Upload documents (.pdf, .md, .txt), ask questions in natural language and get answers grounded
in those documents with verifiable citations, or an explicit "not enough evidence".

Architecture: React SPA → FastAPI → PostgreSQL + pgvector, with the LLM providers behind
ports and adapters. Provider and model names come from configuration, never from code.

## Quick setup

Requirements: Docker with Compose v2.24 or newer. Nothing else needs to be installed on the host.

```bash
cp .env.example .env      # then fill in CHAT_MODEL and OPENAI_API_KEY
docker compose up --build --wait
```

`--wait` returns once the three services are healthy:

| Service    | URL                     | Notes                                                        |
| ---------- | ----------------------- | ------------------------------------------------------------ |
| `frontend` | http://localhost:8080   | Vite build served by nginx; `/api/*` is proxied to the API   |
| `backend`  | http://localhost:8000   | FastAPI; interactive docs at `/docs`                         |
| `db`       | `localhost:5432`        | PostgreSQL 17 + pgvector; local-only credentials `cwyd/cwyd` |

All ports are bound to `127.0.0.1`. Stop with `docker compose down`; add `-v` to also delete the
database volume.

### Configuration

Every variable is listed in [`.env.example`](.env.example).

| Variable            | Required                       | Purpose                                         |
| ------------------- | ------------------------------ | ----------------------------------------------- |
| `CHAT_PROVIDER`     | yes                            | `openai` or `anthropic`                         |
| `CHAT_MODEL`        | yes                            | Chat model name for the selected provider       |
| `EMBEDDING_MODEL`   | yes                            | OpenAI embedding model                          |
| `OPENAI_API_KEY`    | yes                            | Embeddings always use OpenAI                    |
| `ANTHROPIC_API_KEY` | when `CHAT_PROVIDER=anthropic` | Anthropic chat model                            |
| `POSTGRES_*`        | no                             | Local database credentials (default `cwyd`)     |
| `MAX_UPLOAD_MB`     | no (10)                        | Upload size limit; larger files get `413`       |
| `EMBEDDING_DIMENSIONS` | no (1536)                   | Must match the `vector` column of the migration |
| `CHUNK_SIZE`        | no (1000)                      | Chunk size in characters                        |
| `CHUNK_OVERLAP`     | no (150)                       | Overlap between chunks; smaller than the size   |
| `DEFAULT_OWNER_ID`  | no                             | Owner of every document (single-user MVP)       |
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
the dependency is not there. Compose uses it as the backend health check, and the frontend only
starts once the backend is ready.

## Documents

Upload `.pdf` (with selectable text), `.md` or `.txt` files up to `MAX_UPLOAD_MB`. Indexing runs
in the background: the upload answers `202` with status `indexing`; poll until `ready` or
`failed`.

```bash
curl -s -F file=@backend/tests/fixtures/documents/expense-policy.pdf localhost:8000/documents
curl -s localhost:8000/documents/<id>   # {"status":"ready","chunk_count":N,...}
curl -s localhost:8000/documents        # all documents, newest first
```

- Uploading the same file again returns the existing document (`200`) instead of a copy. A
  document that failed with `indexing_failed` (temporary: embeddings provider or database
  unavailable) is indexed again on re-upload (`202`, same id); `no_extractable_text` (for
  example a scanned PDF) needs another version of the file.
- Errors use one envelope, `{"code": "...", "detail": "..."}`: `415 unsupported_type`,
  `413 file_too_large`, `400 empty_file`, `404 document_not_found`, `503 database_unavailable`. Through the frontend proxy
  (`:8080/api`), nginx accepts bodies up to 11 MB (10 MB plus multipart overhead) and answers
  larger ones with the same `413 file_too_large` envelope; raise `client_max_body_size` in
  `frontend/nginx/default.conf.template` together with `MAX_UPLOAD_MB`.
- A document left `indexing` by a restart is marked `failed` / `indexing_failed` when the API
  starts; upload it again to retry.
- Every request in [`docs/http/documents.http`](docs/http/documents.http) can be run against the
  Compose stack. Business rules: [`docs/domain-context.md`](docs/domain-context.md) (DOM-01..06).

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
  response carries `provider` and `model`. Logs record outcome, counts, timings, provider and
  model, never the question, prompt, sources or answer.
- Every request in [`docs/http/chat.http`](docs/http/chat.http) can be run against the Compose
  stack; the expected evidence per case is in
  [`backend/tests/fixtures/rag_cases.json`](backend/tests/fixtures/rag_cases.json). Business
  rules: [`docs/domain-context.md`](docs/domain-context.md) (DOM-07..13).

### Database schema

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

## Development

The repository ships a dev container (`.devcontainer/`) with Python 3.14, uv, Node 26 and access
to the host Docker daemon. Open the folder in VS Code or Cursor and choose *Reopen in Container*;
dependencies are installed on creation.

```bash
# backend/
uv run ruff check . && uv run ruff format --check .   # lint
uv run mypy .                                          # typecheck (strict)
uv run pytest                                          # unit + integration (testcontainers)
uv run pytest -m "not integration"                     # fast loop without Docker
RUN_LIVE_TESTS=1 uv run --env-file ../.env pytest -m live  # opt-in: real OpenAI/Anthropic calls
uv run --env-file ../.env uvicorn app.main:app --reload  # API on :8000; uv loads ../.env, the app does not

# frontend/
npm run lint && npm run typecheck && npm test
npm run dev                                            # Vite on :5173, /api → BACKEND_URL (default :8000)
npm run tokens:audit                                   # design tokens: no drift, no hardcoded values
npm run api:types                                      # openapi.json → src/api/schema.d.ts
VITE_API_MOCKS=true npm run dev                        # the app on MSW mocks, no backend needed
```

The frontend is typed from the API contract: `backend/scripts/export_openapi.py` writes the
FastAPI schema to `frontend/openapi.json` without starting the app, `npm run api:types` turns it
into `frontend/src/api/schema.d.ts` (both committed), and every call goes through the
openapi-fetch client in `frontend/src/api/client.ts` on the relative `/api` path. After changing
anything under `backend/app/api/`, regenerate both:
`cd backend && uv run python -m scripts.export_openapi && npm --prefix ../frontend run api:types`.
The MSW handlers used by the Vitest suite and by `VITE_API_MOCKS=true` are typed from the same
schema, so a contract change breaks the frontend typecheck instead of the running app.
`openapi-typescript` declares a TypeScript 5 peer; an `overrides` entry in `frontend/package.json`
runs it on the project's TypeScript 6.

The UI is built with Tailwind v4 and shadcn/ui on a design system extracted from the design
handoff: tokens live in `docs/design-tokens.json` (primitive → semantic → component), the theme in
`frontend/src/styles/theme.css` is generated from it (`npm run tokens:apply`), and the audit fails
on a missing token, a theme value that drifted or a hardcoded color, size or radius in `src/`.
With `npm run dev`, `http://localhost:5173/preview.html` shows every handoff screen composed from
the components with static data (dev only, not part of the build).

The chat adapter contract tests (`tests/contract/`) run both the OpenAI and the Anthropic
adapters offline against a local HTTP stub of the providers' APIs. The `live` tests call the
real APIs and are skipped unless `RUN_LIVE_TESTS=1`; they also need the provider keys and
`LIVE_OPENAI_CHAT_MODEL` / `LIVE_ANTHROPIC_CHAT_MODEL` (each provider is skipped without them).

Integration tests build `db/Dockerfile` and start it with testcontainers, so they need a Docker
daemon but not the Compose stack. To run the API outside Compose, set `DATABASE_URL` (see
`.env.example`). From the dev container, the Compose services are reached at
`host.docker.internal`, e.g. `BACKEND_URL=http://host.docker.internal:8000 npm run dev`. This
works on Docker Desktop (macOS, Windows/WSL), which forwards `host.docker.internal` to the host
loopback. On native Linux Docker Engine it resolves to the bridge gateway, which cannot reach
ports bound to `127.0.0.1`: run the Vite dev server on the host, or bind the ports you need to
the gateway address in a local `compose.override.yaml` (never commit it).

## Repository layout

```
backend/    FastAPI app (app/{domain,application,adapters,api}), Alembic migrations, tests and
            test fixtures (scripts/generate_fixtures.py), OpenAPI export
            (scripts/export_openapi.py), Dockerfile
frontend/   React + Vite SPA (src/components, src/hooks, src/api with the generated schema,
            src/mocks for MSW, src/styles/theme.css), openapi.json, token scripts
            (scripts/tokens), dev-only design preview (preview.html), nginx template, Dockerfile
db/         PostgreSQL image: init scripts for the pgvector extension; the `local` target used
            by Compose also creates the read-only role for the Postgres MCP server
docs/       design tokens, domain rules, HTTP evidence, evaluation reports, curation notes
compose.yaml, .env.example
```
