---
paths:
  - "backend/app/adapters/**"
---

# Backend persistence

- SQL lives only in adapters under `app/adapters/`. Routers and use cases never import
  SQLAlchemy.
- Adapters receive the shared `AsyncEngine` (or a session factory) through `__init__`, wired in
  `app/composition.py`. They never call `create_async_engine` or read settings themselves.
- One engine per process: `create_async_engine(str(settings.database_url), pool_pre_ping=True)`
  with the asyncpg driver (`postgresql+asyncpg://`). Engine options are typed keyword arguments;
  check spelling, mypy cannot (`**kwargs: Any`).
- Short-lived connections: `async with self._engine.connect()` (reads) or `engine.begin()`
  (writes, commits on exit). Never hold a connection across an `await` on another service.
- Raw SQL goes through `text()` with bound parameters (`:owner_id`); never f-strings or `%`
  formatting with values. String literals use single quotes: `"vector"` in double quotes is an
  identifier and fails with `ProgrammingError`.
- Adapters return domain types or plain values (`str | None`), never `Row` or `Result`
  objects.
- Failures while connecting (`DBAPIError`, `OSError`, pool timeout: refused, wrong credentials,
  missing database, server starting up) and connection loss during the query
  (`InterfaceError`, `OperationalError`, `connection_invalidated`) become `DatabaseUnavailable`
  (`from exc`); the whole check is bounded by `asyncio.timeout`. SQL and programming errors
  (`ProgrammingError`) propagate untouched. The API layer decides the status code.
- Tables and indexes belong to the schema setup that arrives with CWYD-3, never to
  `db/init/`, which only holds what must exist before the app (extensions, roles).
