# Other Tools

Never install packages without asking the user first.

## uv

Use uv for all dependency management (`uv add`, `uv remove`, `uv sync`, `uv run`). Commit the lockfile. Never use pip directly.

## Ruff

Use Ruff to lint and format the code. Consider enabling the FastAPI rules (`FAST`).

## mypy

Type checking is mypy in strict mode (`[tool.mypy] strict = true`, with the Pydantic plugin). Never use ty. Every function, route and dependency needs full annotations, including return types; avoid bare `dict`/`list` and implicit `Any`.

## Blocking code in async functions

Run blocking sync code from async code with `asyncio.to_thread`, inside the adapter that owns the call:

```python
import asyncio


def do_blocking_work(name: str) -> str:
    # Some blocking I/O operation
    return f"Hello {name}"


async def do_work(name: str) -> str:
    return await asyncio.to_thread(do_blocking_work, name)
```

Do not add Asyncer. Do not use SQLModel; database access goes through the repository adapters (SQLAlchemy/asyncpg/langchain-postgres), never from routes.

## HTTPX

Use HTTPX for handling HTTP communication (e.g. with other APIs). It supports sync and async usage (`httpx.AsyncClient` in async code).

Prefer it over Requests.
