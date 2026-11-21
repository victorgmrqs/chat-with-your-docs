# CWYD-2 — Local stack smoke evidence

Evidence for the card's required scenarios. Outputs are verbatim; nothing is mocked.

Environment: 2026-11-21, Docker 29.10.0, Docker Compose v5.8.0, branch
`feat/CWYD-2-monorepo-local-env`. Each scenario starts from an empty database volume
(`docker compose down -v`). Commands were run from the dev container, where published ports
live on the host daemon (docker-outside-of-docker). There, `localhost` in the commands below
was `host.docker.internal`.

## local_stack_missing_config

No `.env` file. The database comes up and the backend refuses to start, naming every missing
variable and pointing to `.env.example`. The frontend is never started because it waits for a
healthy backend. `DATABASE_URL` is not listed because Compose provides it.

```text
$ docker compose up --build --wait   # no .env
 ...                                  # Creating / Created / Starting lines trimmed
 Container cwyd-db-1 Healthy
 Container cwyd-backend-1 Starting
 Container cwyd-backend-1 Started
 Container cwyd-backend-1 Waiting
 Container cwyd-backend-1 Error dependency backend failed to start
 Container cwyd-frontend-1 not started: condition "service_healthy" of service "backend" not met
dependency failed to start: container cwyd-backend-1 exited (3)
exit=1
$ docker compose ps -a
SERVICE    STATUS
backend    Exited (3) Less than a second ago
db         Up 8 seconds (healthy)
frontend   Created
$ docker compose logs backend | tail -9
    raise ConfigurationError(message) from None
app.config.ConfigurationError: Invalid configuration:
  - CHAT_PROVIDER: Field required
  - CHAT_MODEL: Field required
  - EMBEDDING_MODEL: Field required
  - OPENAI_API_KEY: Field required
Set these variables in .env (see .env.example) and restart.

ERROR:    Application startup failed. Exiting.
```

The same happens when `.env.example` is copied without filling it in: empty values count as
missing, so the message lists `CHAT_MODEL` and `OPENAI_API_KEY`. That case is covered by
`test_load_settings_empty_variable_counts_as_missing`.

## local_stack_start_success

`.env` copied from `.env.example` with `CHAT_MODEL` and `OPENAI_API_KEY` set to placeholder
values. No LLM is called in this card.

```text
$ docker compose up --build --wait   # .env with CHAT_MODEL and OPENAI_API_KEY set
exit=0
$ docker compose ps
SERVICE    STATUS
backend    Up 11 seconds (healthy)
db         Up 17 seconds (healthy)
frontend   Up 5 seconds (healthy)
$ curl -s -w " HTTP %{http_code}" localhost:8000/health
{"status":"ok"} HTTP 200
$ curl -s -w " HTTP %{http_code}" localhost:8000/health/ready
{"status":"ready","pgvector":"0.8.7"} HTTP 200
$ curl -s -w " HTTP %{http_code}" localhost:8080/api/health
{"status":"ok"} HTTP 200
$ curl -s -w " HTTP %{http_code}" localhost:8080/api/health/ready
{"status":"ready","pgvector":"0.8.7"} HTTP 200
$ curl -s localhost:8080/ | grep -o "<title>.*</title>"
<title>Chat With Your Docs</title>
$ curl -s localhost:8080/documents/123 | grep -o "<title>.*</title>"   # SPA fallback
<title>Chat With Your Docs</title>
$ docker compose exec db psql -U cwyd -d cwyd -tAc "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'"
vector|0.8.7
```

## Readiness and the read-only role

`/health/ready` reports a missing database as 503 while liveness stays up. The MCP role can read
but not write.

```text
$ docker compose exec -e PGPASSWORD=cwyd_readonly db psql -h 127.0.0.1 -U cwyd_readonly -d cwyd -tAc "CREATE TABLE t (id int)"
ERROR:  permission denied for schema public
LINE 1: CREATE TABLE t (id int)
                     ^
$ docker compose stop db && curl -s -w " HTTP %{http_code}" localhost:8000/health/ready
{"detail":"database unavailable"} HTTP 503
$ curl -s -w " HTTP %{http_code}" localhost:8000/health   # liveness unaffected
{"status":"ok"} HTTP 200
```

The `pgvector extension missing` branch is covered by the integration test
`backend/tests/integration/test_readiness.py`, which runs against a database without the
extension.

## Checks

```text
$ (cd backend && uv run ruff check . && uv run ruff format --check .) && npm --prefix frontend run lint   # exit 0
$ (cd backend && uv run mypy .) && npm --prefix frontend run typecheck                                   # exit 0
$ (cd backend && uv run pytest) && npm --prefix frontend test
10 passed, 1 warning         # backend: unit + testcontainers integration
Tests  1 passed (1)          # frontend
```

Manual check: run [`docs/http/health.http`](../http/health.http) against `docker compose up`.
