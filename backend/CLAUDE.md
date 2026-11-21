# backend/ — FastAPI API

<!-- Facts only. Layer conventions: .claude/rules/backend-*.md. Tooling: python-tooling skill. -->

- Python 3.14, uv (`uv.lock` committed), project without packaging (`--no-package`).
- Layout: `app/{domain,application,adapters,api}`; composition root `app/composition.py`;
  app factory `app/main.py` (`create_app`, settings loaded in the lifespan, not at import).
- Configuration: `app/config.py` (pydantic-settings). `load_settings()` raises
  `ConfigurationError` naming every missing or empty variable. New settings go there and in
  `.env.example` + README.
- Health: `GET /health` (liveness, no I/O) and `GET /health/ready` (database + pgvector, 503
  otherwise). Routes have no `/api` prefix; nginx and the Vite proxy strip it.
- Tests: `tests/unit` (no I/O), `tests/integration` (marker `integration`, PostgreSQL from
  testcontainers, image built from `db/Dockerfile`, session-scoped). Fixtures live in
  `tests/conftest.py`; shared builders in `tests/factories.py` (tests never import conftest).

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run pytest                    # -m "not integration" to skip Docker
```

- Image: `Dockerfile` (uv multi-stage, `uv sync --locked --no-dev`, non-root uid 10001).
