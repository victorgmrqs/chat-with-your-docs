> Part of the `testing-guide-cwyd-backend` skill (see `../SKILL.md`).

# Settings (`BaseSettings` subclasses in `app/config.py`)

## What to test
- Success: all required variables present → typed values (`SecretStr` exposes the value only
  through `get_secret_value()`).
- Every missing variable is named in one `ConfigurationError` message, with the pointer to
  `.env.example`.
- Empty values count as missing (`env_ignore_empty=True`).
- Cross-field rules (`model_validator(mode="after")`), e.g. `CHAT_PROVIDER=anthropic` requires
  `ANTHROPIC_API_KEY`. Model-level errors have an empty `loc`; the message must still read well.
- Closed sets (`Literal`) list the accepted values when an unknown one is given.

## Layer assignment
- Unit only. Settings read the process environment; no other system is involved.
- New flags with branching (`RERANK_ENABLED`) get a unit test here and a behavior test where the
  flag is consumed (use case or adapter).

## Setup pattern
```python
REQUIRED_ENV = {"DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/db", ...}

@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Start every test from a clean environment, whatever the shell exports."""
    for name in (*REQUIRED_ENV, "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch

def test_load_settings_<rule>(env: pytest.MonkeyPatch) -> None:
    for name, value in REQUIRED_ENV.items():
        env.setenv(name, value)
    env.setenv("CHAT_PROVIDER", "anthropic")
    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()
    assert "ANTHROPIC_API_KEY" in str(exc_info.value)
```
- Clear every variable the model reads, including optional ones, so the developer's shell or
  dev container env cannot leak in. When a `.env` file is configured on the model, pass
  `_env_file=None` in tests.
- Other tests never go through the environment: they build `Settings` with the factory in
  `tests/conftest.py` (`Settings.model_validate({...})`).

## When to skip
- Plain `str` fields without rules beyond "required" are covered by the missing-variables test.
- Do not test pydantic's own type coercion (int parsing, URL schemes) unless the project relies
  on a specific rejection.

## Examples from project
- `Settings` / `load_settings` — branching (provider rule, message building) → unit:
  `tests/unit/test_config.py` (success, missing named, empty as missing, anthropic key,
  unknown provider).
