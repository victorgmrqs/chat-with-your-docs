> Part of the `testing-guide-cwyd-backend` skill (see `../SKILL.md`).

# Gotchas

- **`TestClient(app)` without `with` skips the lifespan.** The container is never built and
  routes fail with `AttributeError` on `app.state.container`. Always
  `with TestClient(create_app(settings=...)) as client:`.
- **`httpx` deprecation warning.** Starlette's TestClient now prefers `httpx2` (Pydantic's
  maintained fork of httpx 0.28) and warns when it falls back to `httpx`. Adding `httpx2` to the
  dev group silences it; until then the warning is expected, so do not turn on
  `filterwarnings = error` globally.
- **Event loop scope.** Both `asyncio_default_fixture_loop_scope` and
  `asyncio_default_test_loop_scope` are `session`. Setting only the fixture scope does not move
  tests to the session loop. A session engine used from a different loop fails with "attached to
  a different loop"; dispose engines in fixture teardown (`await engine.dispose()`).
- **`@pytest.mark.asyncio(scope=...)` is deprecated** in pytest-asyncio 1.x; use `loop_scope=`
  if a marker is ever needed (auto mode makes it unnecessary).
- **SQL string literals.** `WHERE extname = "vector"` is an identifier and raises
  `ProgrammingError`; use single quotes or bound parameters. A broad `except` in the code under
  test would hide this as a 503, which is why adapters translate only failures while connecting into
  `DatabaseUnavailable`; query errors propagate.
- **asyncpg connection errors are not all `OperationalError`.** Wrong password, missing database
  and "starting up" arrive as plain `DBAPIError`; catch the connect step, not the error class.
- **mypy cannot check engine keyword arguments** (`create_async_engine(**kwargs: Any)`): a typo
  such as `pool_pre_pring` only fails at runtime, so the composition root must be exercised by a
  test.
- **Container startup.** The pgvector image takes a few seconds; keep `postgres` session-scoped
  and do not start containers per test. Run `-m "not integration"` for a fast loop.
- **Docker-outside-of-docker.** Containers started from the dev container live on the host
  daemon: reach them through `host.docker.internal` (already set via
  `TESTCONTAINERS_HOST_OVERRIDE`); bind mounts resolve on the host.
- **`testcontainers.community.postgres` is a community module** (best effort, can change in a
  minor release). Pin testcontainers in `uv.lock` and read the changelog before upgrading.
- **`testcontainers[postgres]` does not install a driver.** asyncpg is a runtime dependency of
  the app, so it is present; do not add psycopg just for tests.
- **Environment leaks.** The dev container and CI may export real variables; settings tests
  must `delenv` every variable they depend on, including optional ones.
- **`GenericFakeChatModel` consumes its iterator.** Build a new `iter([...])` per test; a shared
  module-level instance returns nothing on the second test.
