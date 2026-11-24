> Part of the `testing-guide-cwyd-backend` skill (see `../SKILL.md`).

# File conventions

```
backend/tests/
  conftest.py        # fixtures only (factories: settings_for, unreachable_settings)
  fakes.py           # port fakes (FakeChatModel, FakeEmbeddings, FakeRetriever...) — importable
  factories.py       # domain object builders — importable
  fixtures/documents/  # generated sample documents with known facts
  unit/              # domain, use cases, settings, HTTP routes without a database
  integration/       # anything that starts PostgreSQL (testcontainers)
```

- File names: `test_<module>.py`. Test names: `test_<unit>_<scenario>` describing behavior
  (`test_ready_is_unavailable_without_the_vector_extension`).
- Integration modules declare `pytestmark = pytest.mark.integration`; markers are strict
  (`--strict-markers`), so new markers are declared in `pyproject.toml`.
- Imports use the `app` package root (`from app.config import ...`), never `backend.app`.
  pytest runs with `--import-mode=importlib` and `pythonpath = ["."]`; never import from
  `conftest`.
- Async tests are plain `async def` (auto mode); do not add `@pytest.mark.asyncio`.
- Coverage: no percentage target (pragmatic policy). The §3 checklist in `../SKILL.md` is the
  gate.

## Commands (from `backend/`)

```bash
uv run pytest                        # everything (needs Docker for integration)
uv run pytest -m "not integration"   # fast loop without Docker
uv run pytest tests/integration -x   # integration only, stop at first failure
```
