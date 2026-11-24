> Part of the `testing-guide-cwyd-backend` skill (see `../SKILL.md`).

# Mock health rules

- **Mock at the port boundary.** Use cases get fakes for their ports; adapters get real
  infrastructure (Postgres) or library fakes (langchain-core). Never fake something inside the
  same layer as the unit under test.
- **Fakes over mocks.** A fake is a small class implementing the `Protocol` with real behavior
  (an in-memory list, deterministic vectors). `unittest.mock` objects are for boundaries only:
  clock, external HTTP, providers. At most 3 test doubles per test.
- **Configured libraries are real:** SQLAlchemy engine, pydantic-settings, document parsing
  libraries. Give them test configuration instead of mocking.
- **FastAPI overrides, not patches:** swap dependencies with `app.dependency_overrides[dep]`;
  never `monkeypatch` module globals or `app.state`.
- **Environment:** `monkeypatch.setenv/delenv` only in settings tests; everything else receives
  a `Settings` object from the factory.
- **Litmus test:** describe what the test proves without mentioning a double. "The chat model is
  not called when nothing is retrieved" is behavior (cost and refusal); "the repository's
  `save` was called once" is wiring — assert the saved state instead.
- **A unit test with a fake repository does not test the repository.** Its adapter must have an
  integration test against real Postgres.
