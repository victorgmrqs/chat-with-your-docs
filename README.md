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
uv run --env-file ../.env uvicorn app.main:app --reload  # API on :8000; uv loads ../.env, the app does not

# frontend/
npm run lint && npm run typecheck && npm test
npm run dev                                            # Vite on :5173, /api → BACKEND_URL (default :8000)
```

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
            test fixtures (scripts/generate_fixtures.py), Dockerfile
frontend/   React + Vite SPA, nginx template, Dockerfile
db/         PostgreSQL image: init scripts for the pgvector extension; the `local` target used
            by Compose also creates the read-only role for the Postgres MCP server
docs/       HTTP evidence, evaluation reports, curation notes
compose.yaml, .env.example
```
