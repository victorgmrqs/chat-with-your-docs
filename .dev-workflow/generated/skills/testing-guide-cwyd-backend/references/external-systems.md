> Part of the `testing-guide-cwyd-backend` skill (see `../SKILL.md`).

# External systems

| System | Strategy | How |
|---|---|---|
| PostgreSQL 17 + pgvector | **Real** | testcontainers: `DockerImage(path=db/, target="runtime")` + `PostgresContainer(str(image), driver="asyncpg")`, session-scoped |
| OpenAI chat | **Fake** | `FakeChatModel` behind `ChatModelPort` (use cases); langchain-core fakes (adapters) |
| Anthropic chat | **Fake** | same as OpenAI chat |
| OpenAI embeddings | **Fake** | `FakeEmbeddings` port fake; `DeterministicFakeEmbedding(size=<dim>)` in adapters and DB fixtures |

## PostgreSQL + pgvector
- One container per test session (startup cost is paid once), built from `db/Dockerfile` so the
  `vector` extension comes from the same init scripts as Compose; never re-create it in tests.
- Extra databases for negative cases (e.g. `without_vector`) are created in the same container.
- Isolation per test: outer transaction rolled back at teardown, or a unique `owner_id`.
- Tests need a Docker daemon, not the Compose stack. From the dev container
  (docker-outside-of-docker) the container is reached through `host.docker.internal`
  (`TESTCONTAINERS_HOST_OVERRIDE` in `devcontainer.json`).
- Unreachable database: settings pointing at `127.0.0.1:1` (fixture `unreachable_settings`).

## LLM providers
- The suite makes no network calls. Keys in test settings are dummies (`sk-test`).
- Real provider calls happen only in the evaluation script (`docs/eval/`), run by a human with
  real keys, outside pytest.
- Fakes are declared classes in `tests/fakes.py` implementing the port `Protocol`, with
  deterministic output and call recording when the behavior depends on it (e.g. "chat model
  not called when retrieval is empty").
