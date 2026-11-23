# CWYD-26 — httpx2 as the test HTTP client

Run on 2026-11-23 from `backend/` (Starlette 1.10.0, FastAPI 0.165.0, Python 3.14).

## Before the change

`httpx2` 2.16.0 was already in `uv.lock` as a transitive dependency of `anthropic`, `openai` and
`langsmith`, and `starlette.testclient` imports `httpx2` before `httpx`. So on `development` the
`StarletteDeprecationWarning` ("Using `httpx` with `starlette.testclient` is deprecated") was no
longer emitted, but the test client's real dependency was undeclared.

## Change

`[dependency-groups] dev`: `httpx>=0.28.1` → `httpx2==2.16.0`. `uv lock` diff (4 lines, no
version moved):

```diff
-    { name = "httpx" },
+    { name = "httpx2" },
-    { name = "httpx", specifier = ">=0.28.1" },
+    { name = "httpx2", specifier = "==2.16.0" },
```

Installed after `uv sync --locked`: `httpx 0.28.1` (runtime transitive) and `httpx2 2.16.0`.

## Test runs

`uv run pytest -W error::starlette.exceptions.StarletteDeprecationWarning -rw`:

```
======================= 330 passed, 2 skipped in 48.04s ========================
```

`uv run pytest -rw` (no warnings summary section is printed):

```
======================= 330 passed, 2 skipped in 46.90s ========================
```

`-W error::DeprecationWarning` (the card's first option) stops on an unrelated warning: langsmith
calls `asyncio.iscoroutinefunction`. `pyproject.toml` already filters that warning, and a
command-line `-W` overrides the filter. Escalating only Starlette's warning class checks the same
thing without that noise.
