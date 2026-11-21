---
name: python-tooling
description: Use when managing backend Python dependencies with uv or configuring ruff, mypy or pytest. Not for test design (see the tdd skill and backend test rules).
---

## Project overrides

- uv is the only package manager; never call pip. Commit `uv.lock`.
- Type checker is mypy strict. Never ty, never pyright.
- Test conventions live in `.claude/rules/backend-tests.md`.

# Python Tooling

## uv

- Add or remove dependencies with `uv add <pkg>` / `uv add --dev <pkg>` / `uv remove <pkg>`; ask the user before running them.
- `uv sync` installs from the lockfile; `uv run <cmd>` runs inside the project environment (`uv run pytest`, `uv run ruff check`, `uv run mypy .`).
- Never edit `uv.lock` by hand; commit it with every dependency change.
- Dependencies live in `pyproject.toml` only (no `requirements.txt`). Pin a compatible range (`>=x.y,<next-major`) and rely on the lockfile for exact versions.

## ruff

One tool for formatting and linting.

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "ASYNC", "S", "RUF", "FAST"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]  # assert is fine in tests
```

Run `uv run ruff format .` then `uv run ruff check .`. Fix findings rather than adding blanket `# noqa`; if one is needed, scope it to a rule code with a reason.

## mypy (strict)

```toml
[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true
```

- Annotate every function including return types (`-> None`); no bare `dict` / `list`, no implicit `Any`.
- Prefer fixing types over `# type: ignore`; when unavoidable, use `# type: ignore[code]` with a reason.
- Third-party packages without stubs: ask before adding a `types-*` package or an `ignore_missing_imports` override for that module only.

## pytest

Layout:

```
backend/tests/
  unit/          # pure domain and use-case tests, no I/O, fakes for ports
  integration/   # adapters and routes against real PostgreSQL (pgvector image)
  conftest.py    # shared fixtures
```

- Integration tests use the PostgreSQL service from Docker Compose (image `pgvector/pgvector:pg17`); create schema per test session and isolate tests with transactions or truncation. Never SQLite or in-memory databases.
- Async code is tested with `pytest-asyncio` (`asyncio_mode = "auto"` in `[tool.pytest.ini_options]`); async fixtures for engine and session.
- LLM and embeddings are replaced by declared fake classes implementing the same port (deterministic output), not ad-hoc patches.
- At most 3 mocks per test. If a test needs more, the unit under test has too many collaborators or the test belongs at integration level.
- Override FastAPI dependencies with `app.dependency_overrides` to inject fakes; do not patch module globals.
- Test names describe behaviour (`test_ingestion_marks_document_failed_when_parsing_raises`).

```bash
uv run pytest tests/unit
uv run pytest tests/integration   # requires the Compose database to be up
```

## Dependency hygiene

- Add a dependency only when the standard library or an existing dependency cannot do the job; state why when asking.
- Keep runtime and dev dependencies separate (`uv add --dev`).
- Review the lockfile diff after any change; never run `uv add` loops or bulk upgrades without approval.
- Before finishing a change, run: `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy .`, `uv run pytest` (scope as appropriate).
