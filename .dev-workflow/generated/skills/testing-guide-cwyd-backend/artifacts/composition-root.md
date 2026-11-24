> Part of the `testing-guide-cwyd-backend` skill (see `../SKILL.md`).

# Composition root (`build_container`, `Container` in `app/composition.py`; `create_app` in `app/main.py`)

## What to test
- The app starts: the lifespan builds the `Container` from `Settings` without touching the
  network (the engine is lazy) and disposes it on shutdown.
- Each new wiring path (a new adapter, a provider selected by `CHAT_PROVIDER`) is exercised by
  at least one test that goes through it, so a wrong constructor argument or a misspelled engine
  option fails in the suite (mypy cannot check `**kwargs`).
- Provider selection by configuration: `openai` vs `anthropic` builds the matching adapter.

## Layer assignment
- **HTTP (TestClient)**: entering `with TestClient(create_app(settings=...))` is the
  "module compilation test" of this stack. Any route test already proves the base wiring.
- **Unit** for selection logic with branching (provider → adapter class) when it grows beyond
  a dictionary lookup: call `build_container(settings)` and assert the adapter type held by the
  container; no network is used because clients are created lazily.

## Setup pattern
```python
def test_build_container_selects_<provider>_chat_adapter() -> None:
    settings = make_settings(...)            # factory from tests/conftest.py
    container = build_container(settings)
    assert isinstance(container.chat_model, AnthropicChatModel)
```

## When to skip
- No test that only asserts `app.state.container` exists or that `include_router` was called.
- Do not assert on the number of providers or routes.

## Examples from project
- `create_app` + `build_container` — no branching yet → covered by every `TestClient` test
  (`tests/unit/test_health.py`, `tests/integration/test_readiness.py`).
