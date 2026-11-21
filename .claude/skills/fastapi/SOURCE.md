# Source

- Upstream: https://github.com/fastapi/fastapi
- Path: `.agents/skills/fastapi`
- Commit: 05e6df7e906c3decba377c37548019973f40bf15
- License: MIT (see `LICENSE`)
- Vendored: 2026-11-20
- Modified: yes

## Modifications

- Frontmatter: narrowed `description`, removed `allowed-tools`, kept `license`; added `## Project overrides`.
- Removed FastAPI Cloud, frontend serving (`app.frontend`), request body limits, OpenTelemetry and `fastapi` CLI / `[tool.fastapi]` sections.
- `async def` is now the default; blocking calls go through `asyncio.to_thread` in adapters.
- Removed SQLModel and Asyncer guidance; tooling is uv + ruff + mypy strict (ty removed).
- Added "Thin routes, use cases via DI" and "Background tasks" sections; replaced the `db.query` route example with a session dependency note.
- Added return annotations (mypy strict) to examples.
- Newer features (`fastapi.sse`, `Depends(max_concurrency=...)`) marked "verify against the pinned FastAPI version"; `[tool.fastapi]`, `max_body_size`, `telemetry=` removed.

## Dropped files

- `references/fastapi-cloud.md`
